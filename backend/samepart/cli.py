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
from samepart.services.live import LiveCatalogue
from samepart.synth.generate import ORGS, generate

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
    stats()


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
    {"seed": seed, "stats": stats}[cmd]()
