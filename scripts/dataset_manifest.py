"""One row per input file, with what a judge would want to know about it.

Every number here is computed from the file itself, the labels file, or the seeded database —
nothing typed in — so the manifest is regenerated with the data and cannot drift from it.
Material masters, procurement histories, the ground-truth labels, the classification backbone
and the dictionaries are all inputs, and all appear, because "what did you feed it" is the
first question about any benchmark.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from samepart.db.models import ExtractedAttribute, Organisation, SourceRecord  # noqa: E402
from samepart.db.session import session_scope  # noqa: E402

import os  # noqa: E402

GEN = Path(os.getenv("SAMEPART_DATA_DIR") or ROOT / "data" / "generated")
OUT = GEN / "dataset_manifest.csv"

COLUMNS = [
    "file", "kind", "organisation", "family", "house_style", "rows", "columns", "size_kb",
    "distinct_identities", "identities_with_2plus_codes_here", "codes_per_identity_mean",
    "pct_with_manufacturer_and_mpn", "pct_with_unit_price", "distinct_uom",
    "pct_with_stock_on_hand", "unique_descriptions", "verbatim_duplicate_descriptions",
    "pct_attributes_unknown_after_extraction", "po_lines", "po_date_from", "po_date_to",
    "po_spend_inr", "distinct_vendors", "distinct_plants", "notes",
]


def read(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}" if d else ""


def main() -> int:
    styles = yaml.safe_load((ROOT / "dictionaries" / "house_styles.yaml").read_text())
    style_of = {o["code"]: o["style"] for o in styles["organisations"]}
    style_label = {k: v["label"] for k, v in styles["styles"].items()}
    name_of = {o["code"]: o["name"] for o in styles["organisations"]}

    labels = read(GEN / "labels.csv")
    identity_of = {(r["org"], r["source_code"]): r["truth_identity"] for r in labels}

    # Unknown-attribute rate per (org, family), from what extraction actually produced.
    unknown: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    with session_scope() as db:
        orgs = {o.id: o.code for o in db.scalars(select(Organisation))}
        rec = {r.id: (orgs[r.org_id], r.family) for r in db.scalars(select(SourceRecord))}
        for a in db.scalars(select(ExtractedAttribute)):
            key = rec.get(a.record_id)
            if not key:
                continue
            unknown[key][1] += 1
            unknown[key][0] += a.status in ("unknown", "unresolvable")

    rows_out: list[dict] = []
    totals = Counter()

    for path in sorted(GEN.glob("*__*.csv")):
        org, family = path.stem.split("__")
        rows = read(path)
        ids = [identity_of.get((org, r["source_code"])) for r in rows]
        per_identity = Counter(i for i in ids if i)
        desc = Counter(" ".join(r["description"].split()).lower() for r in rows)
        u = unknown.get((org, family), [0, 0])
        rows_out.append({
            "file": path.name, "kind": "material master (simulated)", "organisation": org,
            "family": family, "house_style": style_label.get(style_of.get(org, ""), ""),
            "rows": len(rows), "columns": len(rows[0]) if rows else 0,
            "size_kb": round(path.stat().st_size / 1024, 1),
            "distinct_identities": len(per_identity),
            "identities_with_2plus_codes_here": sum(1 for n in per_identity.values() if n > 1),
            "codes_per_identity_mean": f"{len(rows) / len(per_identity):.2f}" if per_identity else "",
            "pct_with_manufacturer_and_mpn": pct(sum(1 for r in rows if r["manufacturer"] and r["mfr_part_no"]), len(rows)),
            "pct_with_unit_price": pct(sum(1 for r in rows if r["unit_price"]), len(rows)),
            "distinct_uom": len({r["uom"] for r in rows}),
            "pct_with_stock_on_hand": pct(sum(1 for r in rows if float(r["stock_on_hand"] or 0) > 0), len(rows)),
            "unique_descriptions": len(desc),
            "verbatim_duplicate_descriptions": sum(n - 1 for n in desc.values() if n > 1),
            "pct_attributes_unknown_after_extraction": pct(u[0], u[1]),
            "notes": f"{name_of.get(org, org)}; every vendor and plant marked (sim)",
        })
        totals["rows"] += len(rows)
        totals["dup_identities"] += sum(1 for n in per_identity.values() if n > 1)
        totals["verbatim"] += sum(n - 1 for n in desc.values() if n > 1)
        totals["unk"] += u[0]; totals["attrs"] += u[1]

    for path in sorted(GEN.glob("*_procurement.csv")):
        org = path.stem.split("_")[0]
        rows = read(path)
        dates = sorted(r["po_date"] for r in rows if r["po_date"])
        spend = sum(float(r["quantity"] or 0) * float(r["unit_price"] or 0) for r in rows)
        rows_out.append({
            "file": path.name, "kind": "procurement history (simulated)", "organisation": org,
            "rows": len(rows), "columns": len(rows[0]) if rows else 0,
            "size_kb": round(path.stat().st_size / 1024, 1),
            "po_lines": len(rows), "po_date_from": dates[0] if dates else "",
            "po_date_to": dates[-1] if dates else "", "po_spend_inr": f"{spend:.0f}",
            "distinct_vendors": len({r["vendor"] for r in rows}),
            "distinct_plants": len({r["plant"] for r in rows}),
            "notes": "PO lines keyed to source_code; prices in issue units, normalised to base units on import",
        })
        totals["po_lines"] += len(rows); totals["spend"] += spend

    ids_all = Counter(r["truth_identity"] for r in labels)
    rows_out.append({
        "file": "labels.csv", "kind": "ground truth", "rows": len(labels), "columns": 3,
        "size_kb": round((GEN / "labels.csv").stat().st_size / 1024, 1),
        "distinct_identities": len([i for i in ids_all if not i.startswith("DEMO-")]),
        "notes": ("truth_identity per source code; held out from the matcher and read only by the "
                  f"evaluation harness; {sum(1 for i in ids_all if i.startswith('DEMO-'))} demo "
                  "fixtures excluded from scoring"),
    })

    tax = ROOT / "data" / "taxonomy" / "unspsc.xlsx"
    if tax.exists():
        rows_out.append({
            "file": "taxonomy/unspsc.xlsx", "kind": "classification backbone (public)",
            "size_kb": round(tax.stat().st_size / 1024, 1),
            "notes": "UNSPSC codeset; each family declares its class (e.g. 31161600 bolts) and the national code carries it",
        })

    for path in sorted((ROOT / "dictionaries").rglob("*.yaml")):
        text = path.read_text()
        rows_out.append({
            "file": f"dictionaries/{path.relative_to(ROOT / 'dictionaries')}",
            "kind": "dictionary (authored)", "rows": text.count("\n"),
            "size_kb": round(path.stat().st_size / 1024, 1),
            "family": path.stem if path.parent.name == "families" else "",
            "notes": "declared, versioned, read at start-up; families, units, gates, house styles, thresholds",
        })

    rows_out.append({
        "file": "TOTAL material masters", "kind": "", "rows": totals["rows"],
        "distinct_identities": len([i for i in ids_all if not i.startswith("DEMO-")]),
        "identities_with_2plus_codes_here": totals["dup_identities"],
        "verbatim_duplicate_descriptions": totals["verbatim"],
        "pct_attributes_unknown_after_extraction": pct(totals["unk"], totals["attrs"]),
        "po_lines": totals["po_lines"], "po_spend_inr": f"{totals['spend']:.0f}",
        "notes": "4 simulated CPSEs x 4 material families; within-CPSE duplicates counted per file",
    })

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows_out:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
