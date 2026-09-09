"""Developer commands.

    python -m samepart.cli seed     generate catalogues and ingest them
    python -m samepart.cli stats    what is currently in the database
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, select

from samepart.api import schemas as s
from samepart.api.deps import dictionary
from samepart.db.models import ExtractedAttribute, Organisation, SourceRecord
from samepart.db.session import init_db, session_scope
from samepart.services.live import LiveCatalogue, LiveReview
from samepart.synth.generate import ORGS, generate
from samepart.synth import procurement as po_synth

DATA = Path("data/generated")


def seed(reset: bool = True) -> None:
    init_db(drop=reset)
    info = generate(DATA)
    print(f"generated {info['records']} records across {len(info['per_org'])} organisations")

    svc = LiveCatalogue(dictionary())
    for code, name in ORGS:
        svc.create_org(code, name)
        path = DATA / f"{code}.csv"
        status = svc.start_import(
            s.ImportRequest(org_code=code, family="hex_bolt"),
            path.name, path.read_bytes(),
        )
        note = f"  {len(status.errors)} warnings" if status.errors else ""
        print(f"  {code}: read {status.rows_read}, ingested {status.rows_ingested}, "
              f"{status.attributes_extracted} attributes{note}")
    _seed_procurement(svc)
    stats()
    match()


def _seed_procurement(svc) -> None:
    import csv as _csv
    cats = {code: list(_csv.DictReader((DATA / f"{code}.csv").open())) for code, _ in ORGS}
    truth = {r["source_code"]: r["truth_identity"]
             for r in _csv.DictReader((DATA / "labels.csv").open())}
    info = po_synth.generate(DATA, cats, truth)
    print(f"\ngenerated {info['total_lines']:,} purchase order lines")
    for code, _ in ORGS:
        st = svc.import_procurement(code, (DATA / f"{code}_procurement.csv").read_bytes())
        print(f"  {code}: {st.rows_ingested:,} lines ingested")


def match() -> None:
    """Retrieve candidates and run the cascade over every pair."""
    info = LiveReview(dictionary()).build_matches()
    print(f"\nmatching: {info['records']} records -> {info['candidate_pairs']:,} candidate pairs "
          f"({info['reduction_ratio']:.2%} of comparisons eliminated)")
    print(f"  blocked on primary key: {info['blocked']}   fell back to text: {info['fallback']}")
    print(f"  written {info['written']}, left alone because already decided {info['already_decided']}")
    for group, n in info["by_group"].items():
        print(f"    {group:<22s} {n:>5d}")
    print(f"  auto-merged without asking anyone: {info['auto_merged']}   "
          f"sampled for audit: {info['sampled_for_audit']}")


def stats() -> None:
    with session_scope() as db:
        records = db.scalar(select(func.count(SourceRecord.id))) or 0
        attrs = db.scalar(select(func.count(ExtractedAttribute.id))) or 0
        unknown = db.scalar(
            select(func.count(ExtractedAttribute.id))
            .where(ExtractedAttribute.status == "unknown")) or 0
        print(f"\ndatabase: {records} records, {attrs} attributes, "
              f"{unknown} unknown ({unknown/attrs:.1%})" if attrs else "database empty")
        for org in db.scalars(select(Organisation).order_by(Organisation.code)):
            n = db.scalar(select(func.count(SourceRecord.id))
                          .where(SourceRecord.org_id == org.id))
            priced = db.scalar(select(func.count(SourceRecord.id))
                               .where(SourceRecord.org_id == org.id,
                                      SourceRecord.unit_price_base.is_not(None)))
            print(f"  {org.code:<6s} {n:>4d} records, {priced} with a base-unit price")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    {"seed": seed, "stats": stats, "match": match}[cmd]()
