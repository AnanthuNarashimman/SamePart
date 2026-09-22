"""Make a demo import file for any CPSE and any family, straight from the registry.

    PYTHONPATH=backend python scripts/demo_import.py NTPC valve_ball

Writes data/demo/<org>_plant2_<family>.csv: a short second-plant catalogue in that
organisation's own house style, built so that one import demonstrates every verdict the
system gives —

  three items the organisation does not hold but two or more others do   → matched across CPSEs
  one item it already holds, written a second way                        → matched to its own code
  one near-miss: an item it holds with one critical attribute changed    → kept separate
  one with a required attribute left unstated                            → a question is asked
  one that exists nowhere                                                → nothing to say

Every row is rendered by the same generator that produced the catalogues, with the same house
style, so a demo file is indistinguishable in form from the data the benchmark was run on.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from samepart.api.deps import dictionary  # noqa: E402
from samepart.db.models import ApprovedMapping, Organisation, SourceRecord  # noqa: E402
from samepart.db.session import session_scope  # noqa: E402
from samepart.synth.generate import STYLE_OF, Identity, _describe  # noqa: E402

OUT = ROOT / "data" / "demo"


def values_of(record: SourceRecord) -> dict:
    out = {}
    for a in record.attributes:
        if a.status in ("unknown", "unresolvable"):
            continue
        v = a.value_text if a.value_text is not None else a.value_number
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        out[a.key] = v
    return out


def main(org: str, family: str, seed: int = 7) -> Path:
    rng = random.Random(seed)
    d = dictionary()
    fam = d.family(family)
    synth = fam.synthesis
    style = STYLE_OF[org]
    numeric = {a.key for a in fam.attributes if a.type == "number"}
    required = [a.key for a in fam.attributes
                if getattr(a, "required_for_decision", False) and a.key in synth.identity_keys]

    with session_scope() as db:
        orgs = {o.id: o.code for o in db.scalars(select(Organisation))}
        groups: dict[str, list[SourceRecord]] = defaultdict(list)
        for m in db.scalars(select(ApprovedMapping)):
            r = db.get(SourceRecord, m.record_id)
            if r and r.family == family:
                groups[m.canonical_id].append(r)

        def holders(rs):
            return {orgs[r.org_id] for r in rs}

        # Members with every identity key extracted, so the rendered line is complete.
        def complete(rs):
            return [r for r in rs if all(k in values_of(r) for k in synth.identity_keys)]

        absent = sorted(((cid, complete(rs)) for cid, rs in groups.items()
                         if org not in holders(rs) and len(holders(rs)) >= 2), key=lambda kv: kv[0])
        absent = [(c, rs) for c, rs in absent if rs][:3]
        held = sorted(((cid, complete(rs)) for cid, rs in groups.items() if org in holders(rs)),
                      key=lambda kv: kv[0])
        held = [(c, rs) for c, rs in held if any(orgs[r.org_id] == org for r in rs)]
        if len(absent) < 3 or len(held) < 2:
            raise SystemExit(f"not enough material for {org}/{family}: {len(absent)} absent, {len(held)} held")

        def render(values: dict, drop: set[str] = frozenset()) -> str:
            ident = Identity(identity_id="demo", family=family, values=values, manufacturer="", mpn="")
            return _describe(synth, ident, style, rng, set(drop))

        rows = []
        n = 0

        def add(desc: str, price: float, note: str):
            nonlocal n
            n += 1
            rows.append({
                "source_code": f"{org}-P2-{n:04d}", "description": desc, "uom": "EA",
                "quantity": 1, "unit_price": f"{price:.2f}", "manufacturer": "", "mfr_part_no": "",
                "stock_on_hand": rng.choice([12, 40, 90, 150, 300, 600]),
                "last_issue_date": f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            })
            print(f"  {rows[-1]['source_code']}  {desc[:64]:<64}  ← {note}")

        for cid, rs in absent:
            r = rs[0]
            add(render(values_of(r)), (r.unit_price or 100) * rng.uniform(0.9, 1.15),
                f"held by {sorted(holders(groups[cid]))}, not {org}")

        cid, rs = held[0]
        own = next(r for r in rs if orgs[r.org_id] == org)
        add(render(values_of(own)), (own.unit_price or 100) * rng.uniform(0.9, 1.15),
            f"{org} already holds this as {own.source_code}")

        # Near-miss: the second held item with one critical enum attribute swapped to another
        # value from the pool, chosen so the result is not itself an existing identity.
        cid2, rs2 = held[1] if len(held) > 1 else held[0]
        base = values_of(next(r for r in rs2 if orgs[r.org_id] == org))
        existing = {tuple(str(values_of(r).get(k)) for k in synth.identity_keys)
                    for rs in groups.values() for r in rs}
        swapped = None
        enum_first = [k for k in synth.identity_keys if k not in numeric] + \
                     [k for k in synth.identity_keys if k in numeric]
        for key in enum_first:
            pool = synth.pools.get(key) or []
            for alt in pool:
                if str(alt) == str(base.get(key)):
                    continue
                trial = {**base, key: alt}
                if tuple(str(trial.get(k)) for k in synth.identity_keys) not in existing:
                    swapped = (key, alt, trial)
                    break
            if swapped:
                break
        if swapped:
            key, alt, trial = swapped
            add(render(trial), (rs2[0].unit_price or 100) * rng.uniform(0.6, 0.9),
                f"near-miss: {key} {base.get(key)} → {alt}")

        # A required attribute left unstated on an item the organisation holds.
        missing_key = required[0] if required else synth.identity_keys[0]
        add(render(base, drop={missing_key}), (rs2[0].unit_price or 100) * rng.uniform(0.9, 1.1),
            f"no {missing_key} stated → a question")

        # Genuinely new: a numeric identity key pushed past its pool.
        num_key = next((k for k in synth.identity_keys if k in numeric and synth.pools.get(k)), None)
        if num_key:
            top = max(synth.pools[num_key])
            fresh = {**base, num_key: top * 2 if top < 50 else top + 100}
            add(render(fresh), (rs2[0].unit_price or 100) * rng.uniform(2.0, 3.5), "exists nowhere")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{org.lower()}_plant2_{family}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(path)
    return path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1].upper(), sys.argv[2])
