"""Developer commands.

    python -m samepart.cli seed      generate catalogues and ingest them
    python -m samepart.cli stats     what is currently in the database
    python -m samepart.cli evaluate  score the matcher against the labels
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, select

from samepart.api import schemas as s
from samepart.api.deps import dictionary
from samepart.db.models import ExtractedAttribute, Organisation, SourceRecord
from samepart.evaluation import evaluate as run_evaluation
from samepart.db.session import init_db, session_scope
from samepart.services.live import LiveCatalogue, LiveReview, ModelEnrichment
from samepart.synth.generate import ORGS, generate
from samepart.synth import procurement as po_synth

DATA = Path("data/generated")


def seed(reset: bool = True) -> None:
    init_db(drop=reset)
    info = generate(DATA)
    print(f"generated {info['records']} records across {len(info['per_org'])} organisations")

    # One import per organisation per family. The generator writes ORG__family.csv, so this
    # loop needs no list of families — it imports whatever was generated, which is what makes
    # dropping in a new family YAML sufficient.
    svc = LiveCatalogue(dictionary())
    for code, name in ORGS:
        svc.create_org(code, name)
    totals: dict[str, int] = {}
    for path in sorted(DATA.glob("*__*.csv")):
        org_code, family_name = path.stem.split("__", 1)
        status = svc.start_import(
            s.ImportRequest(org_code=org_code, family=family_name),
            path.name, path.read_bytes(),
        )
        totals[org_code] = totals.get(org_code, 0) + status.rows_ingested
        note = f"  {len(status.errors)} warnings" if status.errors else ""
        print(f"  {org_code} / {family_name}: read {status.rows_read}, "
              f"ingested {status.rows_ingested}, "
              f"{status.attributes_extracted} attributes{note}")
    _seed_procurement(svc)
    _label_ground_truth()
    stats()
    # Imports already ran matching on the rows they brought in, so this only picks up
    # anything left over. The summary below reports the database, not this pass.
    match()
    summarise()


def _label_ground_truth() -> None:
    """Copy the generator's answer key onto the records it produced.

    SourceRecord.truth_identity has existed since the schema was written and nothing has ever
    populated it, so labels.csv was being used only to price the synthetic purchase orders.
    Without this the evaluation harness has nothing to score against.

    Labels are written to the database rather than read from the CSV at scoring time so that
    an imported catalogue with no answer key simply has null truth and is skipped, instead of
    silently scoring against the wrong file.
    """
    import csv as _csv

    path = DATA / "labels.csv"
    if not path.exists():
        print("\n  ! labels.csv missing; records left unlabelled")
        return

    truth = {r["source_code"]: r["truth_identity"] for r in _csv.DictReader(path.open())}
    with session_scope() as db:
        n = 0
        for record in db.scalars(select(SourceRecord)):
            tid = truth.get(record.source_code)
            if tid and record.truth_identity != tid:
                record.truth_identity = tid
                n += 1
    print(f"\nlabelled {n:,} records with ground truth from labels.csv")


def _seed_procurement(svc) -> None:
    import csv as _csv
    cats: dict[str, list[dict]] = {}
    for path in sorted(DATA.glob("*__*.csv")):
        org_code = path.stem.split("__", 1)[0]
        cats.setdefault(org_code, []).extend(_csv.DictReader(path.open()))
    truth = {r["source_code"]: r["truth_identity"]
             for r in _csv.DictReader((DATA / "labels.csv").open())}
    info = po_synth.generate(DATA, cats, truth)
    print(f"\ngenerated {info['total_lines']:,} purchase order lines")
    for code, _ in ORGS:
        st = svc.import_procurement(code, (DATA / f"{code}_procurement.csv").read_bytes())
        print(f"  {code}: {st.rows_ingested:,} lines ingested")


def match() -> None:
    """Retrieve candidates and run the cascade over every pair, family by family.

    Blocking keys, gates and comparison rules all come from the family definition, so pairs
    are only ever formed within a family. Running per family is not an optimisation — a bolt
    and a gasket have no attributes in common to compare.
    """
    d = dictionary()
    with session_scope() as db:
        present = sorted({r.family for r in db.scalars(select(SourceRecord))})
    for name in present or ["hex_bolt"]:
        print(f"\n── {name}")
        _report_match(LiveReview(d).build_matches(family_name=name))


def _report_match(info: dict) -> None:
    print(f"matching: {info['records']} records -> {info['candidate_pairs']:,} candidate pairs "
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

    def queued(verdict: str) -> list[int]:
        with session_scope() as db:
            return [m.id for m in db.scalars(
                select(CandidateMatch)
                .where(CandidateMatch.review_state == "queued",
                       CandidateMatch.verdict == verdict)
                .order_by(CandidateMatch.id))]

    def work(ids: list[int], hold: int) -> int:
        todo = ids[:-hold] if hold and len(ids) > hold else ids
        done = 0
        for match_id in todo:
            try:
                svc.decide(match_id, sch.DecisionRequest(
                    action=sch.DecisionAction.APPROVE, reviewer=reviewer,
                    reviewer_role="national_approver",
                    note="baseline: prior review history for demonstration"))
                done += 1
            except (KeyError, ValueError, PermissionError):
                continue
        return done

    merges = queued("same_material")
    approved = work(merges, keep_back)
    print(f"{reviewer} approved {approved} merges; {len(merges) - approved} left in the queue")

    # Substitutes too. Approving one does not merge anything -- it records a conditional
    # link and leaves both identities and both source codes exactly as they were. Without
    # this pass the possible_alternative verdicts stay queued forever, the
    # possible_alternative table stays empty, and the substitute story -- which is the part
    # of the problem statement about interchangeable-but-not-identical parts -- never once
    # appears in the UI despite being implemented end to end.
    alts = queued("possible_alternative")
    linked = work(alts, max(len(alts) // 4, 1))
    print(f"{reviewer} linked {linked} conditional substitutes; "
          f"{len(alts) - linked} left in the queue")
    summarise()


def flis() -> None:
    """Slice the DLA catalogue into a real, labelled evaluation set.

        python -m samepart.cli flis <REFERENCE.zip> <IDENTIFICATION.zip> [max_items]
    """
    from samepart.datasets.flis import build, to_catalogues

    if len(sys.argv) < 4:
        print(flis.__doc__); return
    ref, ident = Path(sys.argv[2]), Path(sys.argv[3])
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
    for path in (ref, ident):
        if not path.exists():
            print(f"  not found: {path}"); return

    print("  reading (streamed, nothing loaded whole)...")
    sliced = build(ref, ident, max_items=limit)
    info = to_catalogues(sliced, Path("data/flis"))
    print(f"  items with 2+ part numbers : {info['items']:,}")
    print(f"  part numbers               : {info['part_numbers']:,}")
    print(f"  TRUE duplicate pairs       : {info['true_pairs']:,}")
    print(f"  most part numbers on one   : {info['max_parts_on_one_item']}")
    print(f"  declared equivalences      : {info['equivalences']:,}")
    print(f"  written to data/flis/       {info['organisations']}")


def evaluate() -> None:
    """Score the matcher against the labels, and fail if a frozen threshold regressed.

    `--check` compares every number against dictionaries/evaluation.yaml and exits non-zero
    on any regression, so CI enforces the benchmark rather than a person remembering to look
    at it. `--json PATH` writes the full report for a slide or a diff.
    """
    import json

    args = sys.argv[2:]
    check = "--check" in args
    out_path = None
    if "--json" in args:
        out_path = Path(args[args.index("--json") + 1])

    with session_scope() as db:
        report = run_evaluation(db)
        families = sorted({r.family for r in db.scalars(select(SourceRecord))})
        per_family = ({name: run_evaluation(db, family=name) for name in families}
                      if len(families) > 1 else {})

    _print_report(report)
    if per_family:
        _print_by_family(per_family)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report.as_dict(), indent=2) + "\n")
        print(f"\n  written to {out_path}")

    if check:
        sys.exit(_check_thresholds(report))


def _print_report(report) -> None:
    def block(title: str, rows: list[tuple[str, object]]) -> None:
        print(f"\n{title}")
        for label, value in rows:
            if isinstance(value, float):
                value = f"{value:.4f}" if value < 1 else f"{value:.2f}"
            print(f"    {label:<34s} {value:>12}")

    print(f"\n{report.records} records, {report.labelled} labelled, "
          f"{report.true_pairs:,} truly-matching pairs among {report.comparisons:,} comparisons")

    if not report.labelled:
        for n in report.notes:
            print(f"  ! {n}")
        return

    rt = report.retrieval
    block("RETRIEVAL  did the pair ever get proposed", [
        ("candidate pairs", f"{rt['candidate_pairs']:,}"),
        ("pairs completeness", rt["pairs_completeness"]),
        ("reduction ratio", rt["reduction_ratio"]),
        ("true pairs never proposed", rt["true_pairs_missed"]),
    ])

    d, pw = report.decision, report.decision["pairwise"]
    block("DECISION  given the pair, was the call right", [
        ("pairwise precision", pw["precision"]),
        ("pairwise recall", pw["recall"]),
        ("pairwise F1", pw["f1"]),
        ("false merges", d["false_merges"]),
        ("  of which evidence conflicted", d["false_merges_with_conflicting_evidence"]),
        ("  of which indistinguishable", d["indistinguishable_pairs"]),
        ("false merge rate", d["false_merge_rate"]),
        ("false separations", d["false_separations"]),
        ("abstained", f"{d['abstained']} ({d['abstention_rate']:.1%})"),
        ("routed as substitute", d["possible_alternative"]),
    ])

    hn = report.hard_negatives
    block("HARD NEGATIVES  look alike, are not the same", [
        ("pairs", f"{hn['pairs']:,}"),
        ("wrongly merged", hn["wrongly_merged"]),
        ("false merge rate", hn["false_merge_rate"]),
        ("correctly separated", hn["correctly_separated"]),
        ("sent to a person", hn["sent_to_a_person"]),
    ])

    o, bc = report.outcome, report.outcome["bcubed"]
    block("OUTCOME  are the final clusters right", [
        ("records mapped", o["records_mapped"]),
        ("clusters formed", f"{o['clusters']} of {o['true_clusters']} true"),
        ("B-cubed precision", bc["precision"]),
        ("B-cubed recall", bc["recall"]),
        ("B-cubed F1", bc["f1"]),
        ("impure clusters", o["impure_clusters"]),
        ("cluster purity", o["cluster_purity"]),
    ])

    if report.price_flag:
        pf = report.price_flag
        block("PRICE VARIANCE  an independent second opinion", [
            ("flag threshold", f"{pf['threshold']}x"),
            ("clusters scored", pf["clusters_scored"]),
            ("flagged", pf["flagged"]),
            ("precision", pf["precision"]),
            ("recall", pf["recall"]),
        ])

    t = report.tiers
    block("COST  which tier settled each pair", [
        *[(name, n) for name, n in t["by_tier"].items()],
        ("share without a model", t["share_without_a_model"]),
    ])

    for n in report.notes:
        print(f"\n  ! {n}")


def _print_by_family(reports: dict) -> None:
    """One line per family.

    This is the proof that families are data: the same pipeline, the same gates engine and the
    same harness, run over four material families none of which is named anywhere in Python.
    Where a family scores worse it is because its attributes are harder to read, not because
    anything was written for it.
    """
    print("\nBY FAMILY")
    head = f"    {'family':<22}{'records':>8}{'P':>8}{'R':>8}{'F1':>8}{'B3 F1':>8}{'purity':>8}{'no model':>10}"
    print(head)
    print("    " + "-" * (len(head) - 4))
    for name, r in sorted(reports.items()):
        pw = r.decision.get("pairwise", {})
        print(f"    {name:<22}{r.records:>8}"
              f"{pw.get('precision', 0):>8.3f}{pw.get('recall', 0):>8.3f}{pw.get('f1', 0):>8.3f}"
              f"{r.outcome.get('bcubed', {}).get('f1', 0):>8.3f}"
              f"{r.outcome.get('cluster_purity', 0):>8.3f}"
              f"{r.tiers.get('share_without_a_model', 0):>10.3f}")


def _check_thresholds(report) -> int:
    """Compare against the frozen benchmark. Returns a process exit code."""
    import yaml

    path = Path("dictionaries/evaluation.yaml")
    if not path.exists():
        print(f"\n  ! {path} not found; nothing to check against.")
        return 1

    spec = yaml.safe_load(path.read_text()) or {}
    flat = report.flat()
    failures, missing = [], []

    for name, rule in (spec.get("thresholds") or {}).items():
        if name not in flat:
            missing.append(name)
            continue
        actual = flat[name]
        if "min" in rule and actual < rule["min"]:
            failures.append((name, f"{actual} < min {rule['min']}", rule.get("why", "")))
        if "max" in rule and actual > rule["max"]:
            failures.append((name, f"{actual} > max {rule['max']}", rule.get("why", "")))

    print(f"\nFROZEN BENCHMARK  {spec.get('frozen_on', 'undated')}")
    if missing:
        for m in missing:
            print(f"    ?  {m} — not produced by this run")
    if failures:
        for name, detail, why in failures:
            print(f"    FAIL  {name}: {detail}")
            if why:
                print(f"          {why}")
        print(f"\n  {len(failures)} threshold(s) regressed.")
        return 1
    print(f"    all {len(spec.get('thresholds') or {})} thresholds hold.")
    return 1 if missing else 0


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
     "enrich": enrich, "baseline": baseline, "flis": flis,
     "evaluate": evaluate}[cmd]()
