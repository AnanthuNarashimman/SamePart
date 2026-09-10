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
from samepart.services.live import LiveCatalogue, LiveReview, ModelEnrichment
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
    # Imports already ran matching on the rows they brought in, so this only picks up
    # anything left over. The summary below reports the database, not this pass.
    match()
    summarise()


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


def summarise() -> None:
    """Report the state of the database, not the state of the last pass."""
    from collections import Counter
    from samepart.db.models import CandidateMatch, CanonicalMaterial
    with session_scope() as db:
        rows = [(m.verdict, m.review_state) for m in db.scalars(select(CandidateMatch))]
        canon = db.scalar(select(func.count(CanonicalMaterial.canonical_id))) or 0
    by_state = Counter(st for _, st in rows)
    by_verdict = Counter(v for v, _ in rows)
    print(f"\nafter matching: {len(rows):,} pairs, {canon} canonical materials")
    for v, n in by_verdict.most_common():
        print(f"    {v:<24s} {n:>5d}")
    print(f"  auto-approved without asking anyone: {by_state.get('auto_approved', 0)}")
    print(f"  waiting for a person:                {by_state.get('queued', 0)}")


def enrich() -> None:
    """Second-pass extraction with the model, for attributes patterns could not read."""
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    info = ModelEnrichment(dictionary()).enrich(limit=n)
    if not info.get("available"):
        print(f"  {info['note']}"); return
    print(f"model {info['model']}: examined {info['records_examined']} records with blanks")
    print(f"  attributes considered : {info['attributes_considered']}")
    print(f"  filled                : {info['filled']}")
    print(f"  abstained             : {info['abstained']}")
    print(f"  rejected, no evidence : {info['rejected_no_evidence']}")
    print(f"  records changed       : {info['records_changed']}   errors: {info['errors']}")


def baseline() -> None:
    """Work the queue as a reviewer would, to give a demo a populated starting point.

    Automation is off, which is the correct posture, but it means nothing is merged until a
    person approves it and the dashboard has nothing to show. A real deployment would have
    months of prior approvals behind it. This produces that history.

    Every approval is recorded against a NAMED reviewer, not as "auto", so the audit trail
    says exactly what happened. It is a demo aid and the trail shows it as one.
    """
    from samepart.api import schemas as sch
    from samepart.db.models import CandidateMatch

    reviewer = sys.argv[2] if len(sys.argv) > 2 else "steward-demo"
    keep_back = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    svc = LiveReview(dictionary())
    with session_scope() as db:
        ids = [m.id for m in db.scalars(
            select(CandidateMatch)
            .where(CandidateMatch.review_state == "queued",
                   CandidateMatch.verdict == "same_material")
            .order_by(CandidateMatch.id))]
    todo = ids[:-keep_back] if keep_back and len(ids) > keep_back else ids

    approved = 0
    for match_id in todo:
        try:
            svc.decide(match_id, sch.DecisionRequest(
                action=sch.DecisionAction.APPROVE, reviewer=reviewer,
                reviewer_role="national_approver",
                note="baseline: prior review history for demonstration"))
            approved += 1
        except (KeyError, ValueError, PermissionError):
            continue
    print(f"{reviewer} approved {approved} merges; {len(ids) - approved} left in the queue")
    summarise()


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
    {"seed": seed, "stats": stats, "match": match, "summary": summarise,
     "enrich": enrich, "baseline": baseline}[cmd]()
