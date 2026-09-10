"""Slicing the US defence logistics catalogue into a real evaluation set.

This is the only public dataset we found carrying genuine "same item, different codes"
ground truth. One permanent item identification number (NIIN) is the canonical identity, and
many manufacturer part numbers, each tied to a manufacturer code, map onto it. That is
precisely the structure SamePart claims to reconstruct, with the answer already known.

Two files are enough:

  REFERENCE.zip       -> V_FLIS_PART.CSV            NIIN, PART_NUMBER, CAGE_CODE
  IDENTIFICATION.zip  -> P_FLIS_NSN.CSV             NSN (FSC + NIIN), item name
                      -> V_FLIS_STANDARDIZATION.CSV NIIN-to-NIIN equivalence

Both are streamed, never loaded whole: 16.4 million rows is not something to hold in memory
to extract a few thousand.

**Say what this is when you present it.** It is US military catalogue data, so it proves the
method rather than the Indian context, and the many codes are manufacturer part numbers
rather than four organisations' internal codes. Structurally the same problem, honestly
described.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Federal Supply Classification groups for threaded fasteners, which is the family we model.
FASTENER_FSC = {
    "5305": "Screws",
    "5306": "Bolts",
    "5307": "Studs",
    "5310": "Nuts and washers",
}


def _open_member(zip_path: Path, endswith: str):
    """Stream one CSV out of a zip without extracting the archive."""
    archive = zipfile.ZipFile(zip_path)
    name = next((n for n in archive.namelist() if n.upper().endswith(endswith.upper())), None)
    if name is None:
        raise FileNotFoundError(
            f"{endswith} not found in {zip_path.name}; it holds {archive.namelist()[:8]}")
    return csv.DictReader(io.TextIOWrapper(archive.open(name), encoding="utf-8",
                                           errors="replace"))


def _col(row: dict, *candidates: str) -> str:
    """Column names drift between FLIS releases, so accept the known variants."""
    for c in candidates:
        for key in row:
            if key.strip().upper().replace("_", "") == c.upper().replace("_", ""):
                return (row[key] or "").strip()
    return ""


@dataclass
class Slice:
    items: dict[str, dict] = field(default_factory=dict)   # niin -> {name, fsc, parts[]}
    equivalences: list[tuple[str, str]] = field(default_factory=list)

    def stats(self) -> dict:
        parts = [len(v["parts"]) for v in self.items.values()]
        pairs = sum(n * (n - 1) // 2 for n in parts)
        return {
            "items": len(self.items),
            "part_numbers": sum(parts),
            "true_pairs": pairs,
            "max_parts_on_one_item": max(parts) if parts else 0,
            "equivalences": len(self.equivalences),
        }


def build(reference_zip: Path, identification_zip: Path,
          fsc: set[str] | None = None, max_items: int = 4000,
          min_parts: int = 2) -> Slice:
    """Take items in the chosen supply classes that carry several part numbers.

    An item with only one part number teaches nothing: there is no pair to get right or
    wrong. `min_parts` keeps only the ones that constitute actual ground truth.
    """
    fsc = fsc or set(FASTENER_FSC)
    wanted: dict[str, dict] = {}

    for row in _open_member(identification_zip, "P_FLIS_NSN.CSV"):
        niin = _col(row, "NIIN")
        code = _col(row, "FSC", "FSG")
        if not niin:
            continue
        if not code:
            nsn = _col(row, "NSN")
            code = nsn[:4] if len(nsn) >= 4 else ""
        if code in fsc:
            wanted[niin] = {"fsc": code, "fsc_label": FASTENER_FSC.get(code, code),
                            "name": _col(row, "ITEM_NAME", "INC_NAME", "APPROVED_ITEM_NAME"),
                            "parts": []}
        if len(wanted) >= max_items * 6:      # gather a surplus; most have one part number
            break

    for row in _open_member(reference_zip, "V_FLIS_PART.CSV"):
        niin = _col(row, "NIIN")
        entry = wanted.get(niin)
        if entry is None:
            continue
        part = _col(row, "PART_NUMBER", "REFERENCE_NUMBER")
        cage = _col(row, "CAGE_CODE", "CAGE")
        if part:
            entry["parts"].append({"part_number": part, "cage": cage})

    kept = {n: v for n, v in wanted.items() if len(v["parts"]) >= min_parts}
    kept = dict(sorted(kept.items(), key=lambda kv: -len(kv[1]["parts"]))[:max_items])

    equivalences: list[tuple[str, str]] = []
    try:
        for row in _open_member(identification_zip, "V_FLIS_STANDARDIZATION.CSV"):
            a, b = _col(row, "NIIN"), _col(row, "RELATED_NIIN", "REPLACEMENT_NIIN", "NIIN_2")
            if a in kept and b in kept and a != b:
                equivalences.append((a, b))
    except FileNotFoundError:
        pass

    return Slice(items=kept, equivalences=equivalences)


def to_catalogues(sliced: Slice, out_dir: Path, organisations: int = 4) -> dict:
    """Turn the slice into per-organisation catalogues in our own import format.

    Each manufacturer part number for one item becomes one organisation's record, which is
    exactly the real situation: several parties holding their own code for the same physical
    item. The item number is the truth label and is written to a separate file, so the
    pipeline cannot read the answer.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    orgs = [f"ORG{i + 1}" for i in range(organisations)]
    rows: dict[str, list[dict]] = {o: [] for o in orgs}
    labels: list[tuple[str, str, str]] = []
    counters = {o: 1 for o in orgs}

    for niin, entry in sliced.items.items():
        for i, part in enumerate(entry["parts"]):
            org = orgs[i % len(orgs)]
            code = f"{org}-{counters[org]:06d}"
            counters[org] += 1
            rows[org].append({
                "source_code": code,
                "description": " ".join(x for x in [entry["name"], part["part_number"]] if x),
                "uom": "EA", "quantity": 1, "unit_price": "",
                "manufacturer": part["cage"], "mfr_part_no": part["part_number"],
            })
            labels.append((org, code, niin))

    for org, items in rows.items():
        if not items:
            continue
        with (out_dir / f"{org}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(items[0]))
            w.writeheader()
            w.writerows(items)
    with (out_dir / "labels.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["org", "source_code", "truth_identity"])
        w.writerows(labels)
    (out_dir / "provenance.json").write_text(json.dumps({
        "source": "US Defense Logistics Agency, public FLIS extract",
        "licence": "US Government work, effectively public domain",
        "caveat": ("US military catalogue data. Proves the matching method, not the Indian "
                   "procurement context. The several codes per item are manufacturer part "
                   "numbers, not four organisations' internal material codes."),
        **sliced.stats(),
    }, indent=2))
    return {"organisations": {o: len(v) for o, v in rows.items()}, **sliced.stats()}
