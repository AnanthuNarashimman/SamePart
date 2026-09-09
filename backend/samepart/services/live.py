"""Live service implementations, backed by the database and the pipeline.

Each class satisfies one protocol in `protocols.py` and is selected in `api/deps.py`. They
are added one at a time; anything not yet implemented stays on its stub, and the frontend
cannot tell the difference.
"""
from __future__ import annotations

import random
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import func, select

from samepart.api import schemas as s
from samepart.db.models import ExtractedAttribute, Organisation, SourceRecord
from samepart.db.session import session_scope
from samepart.dictionary.loader import Dictionary
from samepart.ingest.csv_loader import Row, load_csv
from samepart.pipeline.extract import extract

# Import status is held in memory. Ingestion is synchronous and fast at this scale; when it
# becomes a background job this moves to a table.
_IMPORTS: dict[str, s.ImportStatus] = {}

_GIVEN_KEYS = ("manufacturer", "manufacturer_part_number")


class LiveCatalogue:
    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    # -- reads -------------------------------------------------------------
    def list_orgs(self) -> list[s.Org]:
        with session_scope() as db:
            counts = dict(
                db.execute(
                    select(SourceRecord.org_id, func.count(SourceRecord.id))
                    .group_by(SourceRecord.org_id)
                ).all()
            )
            return [
                s.Org(code=o.code, name=o.name, simulated=o.simulated,
                      record_count=counts.get(o.id, 0))
                for o in db.scalars(select(Organisation).order_by(Organisation.code))
            ]

    def create_org(self, code: str, name: str) -> s.Org:
        with session_scope() as db:
            existing = db.scalar(select(Organisation).where(Organisation.code == code))
            if existing:
                existing.name = name
                return s.Org(code=existing.code, name=existing.name,
                             simulated=existing.simulated)
            org = Organisation(code=code, name=name)
            db.add(org)
            db.flush()
            return s.Org(code=org.code, name=org.name, simulated=org.simulated)

    # -- writes ------------------------------------------------------------
    def start_import(self, req: s.ImportRequest, filename: str, content: bytes) -> s.ImportStatus:
        import_id = str(uuid.uuid4())[:8]
        family = self.dictionary.family(req.family)
        result = load_csv(content, self.dictionary.units, req.column_map)

        status = s.ImportStatus(
            import_id=import_id, org_code=req.org_code, status="running",
            rows_read=result.rows_read, errors=list(result.errors[:50]),
            started_at=datetime.now(timezone.utc),
        )
        if result.errors and not result.rows:
            status.status = "failed"
            _IMPORTS[import_id] = status
            return status

        ingested = attributes = 0
        with session_scope() as db:
            org = db.scalar(select(Organisation).where(Organisation.code == req.org_code))
            if org is None:
                org = Organisation(code=req.org_code, name=f"{req.org_code} (simulated)")
                db.add(org)
                db.flush()

            existing = set(
                db.scalars(
                    select(SourceRecord.source_code).where(SourceRecord.org_id == org.id)
                )
            )
            for row in result.rows:
                if row.source_code in existing:
                    status.errors.append(
                        f"{row.source_code}: already imported for {req.org_code}, skipped")
                    continue
                existing.add(row.source_code)
                record = self._persist(db, org.id, family.family, row)
                ingested += 1
                attributes += self._extract_into(db, record, row)

        status.status = "completed"
        status.rows_ingested = ingested
        status.attributes_extracted = attributes
        _IMPORTS[import_id] = status
        return status

    def import_status(self, import_id: str) -> s.ImportStatus:
        try:
            return _IMPORTS[import_id]
        except KeyError:
            raise KeyError(import_id) from None

    # -- internals ---------------------------------------------------------
    def _persist(self, db, org_id: int, family: str, row: Row) -> SourceRecord:
        record = SourceRecord(
            org_id=org_id, source_code=row.source_code, raw_description=row.description,
            family=family, raw_uom=row.uom, base_uom=row.base_uom,
            quantity=row.quantity, base_quantity=row.base_quantity,
            unit_price=row.unit_price, unit_price_base=row.unit_price_base,
            row_ref=row.row_ref,
        )
        db.add(record)
        db.flush()
        return record

    def _extract_into(self, db, record: SourceRecord, row: Row) -> int:
        """Regex extraction, plus the fields the source stated outright.

        Attributes regex cannot fill are stored with status `unknown` rather than omitted.
        A missing critical attribute is the reason the system asks a question, so it has to
        survive into the database and onto the screen.
        """
        family = self.dictionary.family(record.family)
        values = extract(family, row.description)
        written = 0

        for key, v in values.items():
            given = getattr(row, key, None) if key in _GIVEN_KEYS else None
            if given:
                value, status, method, evidence = given, "extracted", "given", "stated by source"
            elif v.value is None:
                value, status, method, evidence = None, "unknown", v.method, None
            else:
                value, status, method, evidence = v.value, v.status, v.method, v.evidence

            db.add(ExtractedAttribute(
                record_id=record.id, key=key,
                value_number=float(value) if isinstance(value, (int, float)) else None,
                value_text=None if isinstance(value, (int, float)) or value is None else str(value),
                unit=v.unit, status=status, method=method, evidence=evidence,
                confidence=v.confidence if value is not None else None,
            ))
            written += 1
        return written


# ---------------------------------------------------------------------------
# Review: the queue, the comparison, and the human decision
# ---------------------------------------------------------------------------
from sqlalchemy.orm import selectinload  # noqa: E402

from samepart.db.models import (ApprovedMapping, CandidateMatch, CanonicalMaterial,  # noqa: E402
                                DecisionEvent, KnownConflict, PossibleAlternative)
from samepart.gates import Verdict as GateVerdict  # noqa: E402
from samepart.pipeline import cascade, registry  # noqa: E402
from samepart.pipeline.retrieval import Retriever  # noqa: E402

_GROUP_OF = {
    GateVerdict.INSUFFICIENT_EVIDENCE.value: "needs_input",
    GateVerdict.POSSIBLE_ALTERNATIVE.value: "possible_alternative",
    GateVerdict.SAME.value: "same_material",
    GateVerdict.DIFFERENT.value: "different",
}
_GROUP_ORDER = ["needs_input", "possible_alternative", "same_material", "different"]

_HEADLINE = {
    "needs_input": "Cannot decide safely: {detail}",
    "possible_alternative": "Conditional substitute: {detail}",
    "same_material": "Same material, described differently",
    "different": "Different material: {detail}",
}


class LiveReview:
    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    # -- building the queue -------------------------------------------------
    def build_matches(self, family_name: str = "hex_bolt", verbose: bool = False) -> dict:
        """Retrieve candidates, run the cascade, persist a verdict for every pair.

        Idempotent: existing rows are refreshed rather than duplicated, and any pair a
        human has already decided is left alone.
        """
        family = self.dictionary.family(family_name)
        with session_scope() as db:
            records = list(db.scalars(
                select(SourceRecord)
                .where(SourceRecord.family == family_name)
                .options(selectinload(SourceRecord.attributes))
            ))
            by_id = {r.id: r for r in records}
            retriever = Retriever(family)
            stats = retriever.build([(str(r.id), r.raw_description) for r in records])

            decided = {
                (m.a_id, m.b_id): m
                for m in db.scalars(select(CandidateMatch))
            }
            counts: dict[str, int] = {g: 0 for g in _GROUP_ORDER}
            written = skipped = auto = audit = 0
            policy = family.auto_merge
            rng = random.Random(20260909)

            for sa, sb in retriever.candidate_pairs():
                a_id, b_id = sorted((int(sa), int(sb)))
                a, b = by_id[a_id], by_id[b_id]
                result = cascade.run(family, a.attrs(), b.attrs(),
                                     a.unresolvable(), b.unresolvable())
                counts[_GROUP_OF[result.verdict.value]] += 1

                row = decided.get((a_id, b_id))
                if row is not None and row.review_state != "queued":
                    skipped += 1
                    continue
                if row is None:
                    row = CandidateMatch(a_id=a_id, b_id=b_id)
                    db.add(row)

                row.retrieval_score = 1.0
                row.decided_by = result.decided_by
                row.score = result.score
                row.verdict = result.verdict.value
                row.rationale = result.rationale
                row.gate_overrode = result.gate_overrode
                row.gate_firings = [
                    {"gate_id": f.gate_id, "action": f.action.value, "message": f.message,
                     "attributes": f.attributes, "detail": f.detail}
                    for f in result.gate.firings
                ] + [{"gate_id": "_conditions", "action": "note", "message": c,
                      "attributes": [], "detail": ""}
                     for c in result.gate.substitution_conditions]
                written += 1

                # Nothing to judge, so nobody is asked. A sampled fraction still goes to a
                # person, because an automation rate nobody audits is a claim, not a control.
                if result.auto_mergeable(policy):
                    if rng.random() < policy.audit_sample_rate:
                        row.review_state = "queued"
                        row.rationale = (row.rationale or "") + \
                            " Selected for audit sampling of automatic merges."
                        audit += 1
                    else:
                        db.flush()
                        self._merge(db, a, b, "auto")
                        row.review_state = "auto_approved"
                        auto += 1

        return {"records": stats.records, "candidate_pairs": stats.candidate_pairs,
                "reduction_ratio": round(stats.reduction_ratio, 4),
                "blocked": stats.blocked, "fallback": stats.fallback,
                "written": written, "already_decided": skipped, "by_group": counts,
                "auto_merged": auto, "sampled_for_audit": audit}

    # -- reads --------------------------------------------------------------
    def queue(self, group: str | None, cursor: str | None, limit: int) -> s.QueuePage:
        with session_scope() as db:
            counts = s.QueueCounts()
            for verdict, n in db.execute(
                select(CandidateMatch.verdict, func.count(CandidateMatch.id))
                .where(CandidateMatch.review_state == "queued")
                .group_by(CandidateMatch.verdict)
            ).all():
                setattr(counts, _GROUP_OF[verdict], n)

            q = select(CandidateMatch).where(CandidateMatch.review_state == "queued")
            if group:
                wanted = [v for v, g in _GROUP_OF.items() if g == group]
                q = q.where(CandidateMatch.verdict.in_(wanted))

            offset = int(cursor) if cursor and cursor.isdigit() else 0
            rows = list(db.scalars(q.order_by(CandidateMatch.id).offset(offset).limit(limit + 1)))
            more = len(rows) > limit
            rows = rows[:limit]

            items = []
            for m in rows:
                a = db.get(SourceRecord, m.a_id)
                b = db.get(SourceRecord, m.b_id)
                g = _GROUP_OF[m.verdict]
                detail = next((f.get("detail") for f in (m.gate_firings or []) if f.get("detail")), "")
                items.append(s.QueueItem(
                    id=m.id, verdict=s.Verdict(m.verdict),
                    review_state=s.ReviewState(m.review_state),
                    a_description=a.raw_description, b_description=b.raw_description,
                    a_org=a.org.code, b_org=b.org.code,
                    headline=_HEADLINE[g].format(detail=detail or m.rationale or ""),
                ))
            items.sort(key=lambda i: _GROUP_ORDER.index(_GROUP_OF[i.verdict.value]))
            return s.QueuePage(counts=counts, items=items,
                               next_cursor=str(offset + limit) if more else None)

    def match(self, match_id: int) -> s.MatchDetail:
        with session_scope() as db:
            m = db.get(CandidateMatch, match_id)
            if m is None:
                raise KeyError(match_id)
            firings = [f for f in (m.gate_firings or []) if f.get("gate_id") != "_conditions"]
            conditions = [f["message"] for f in (m.gate_firings or [])
                          if f.get("gate_id") == "_conditions"]
            return s.MatchDetail(
                id=m.id, verdict=s.Verdict(m.verdict), decided_by=m.decided_by or "attributes",
                score=m.score, review_state=s.ReviewState(m.review_state),
                gate_overrode=m.gate_overrode,
                gate_firings=[s.GateFiring(**f) for f in firings],
                substitution_conditions=conditions,
                notes=[m.rationale] if m.rationale else [],
                a=self._record_view(db, m.a_id), b=self._record_view(db, m.b_id),
            )

    def _record_view(self, db, record_id: int) -> s.RecordView:
        r = db.get(SourceRecord, record_id)
        family = self.dictionary.family(r.family)
        by_key = {a.key: a for a in r.attributes}
        attrs = []
        for defn in family.attributes:
            a = by_key.get(defn.key)
            if a is None:
                continue
            value = a.value_number if a.value_number is not None else a.value_text
            attrs.append(s.AttributeView(
                key=a.key, label=defn.label, value=value, unit=a.unit,
                status=s.AttributeStatus(a.status), method=s.ExtractionMethod(a.method),
                evidence=a.evidence, confidence=a.confidence,
                criticality=defn.criticality.value,
            ))
        mapping = db.scalar(select(ApprovedMapping).where(ApprovedMapping.record_id == r.id))
        canonical = db.get(CanonicalMaterial, mapping.canonical_id) if mapping else None
        return s.RecordView(
            record_id=r.id, org_code=r.org.code, source_code=r.source_code,
            raw_description=r.raw_description,
            standardised_short=canonical.standardised_short if canonical else None,
            uom=r.raw_uom, base_uom=r.base_uom, quantity=r.quantity,
            unit_price=r.unit_price, unit_price_base=r.unit_price_base,
            currency=r.currency, attributes=attrs,
        )

    # -- the human decision --------------------------------------------------
    def decide(self, match_id: int, req: s.DecisionRequest) -> s.DecisionResult:
        """Apply a reviewer's decision.

        `approve` means "accept the relationship the system proposed", which is a merge for
        same-material, an alternative link for a conditional substitute, and a permanent
        separation for different. `reject` always records a cannot-link constraint, so a
        rejection is never lost and never re-proposed.

        Nothing here overwrites a source record. Approving adds rows.
        """
        with session_scope() as db:
            m = db.get(CandidateMatch, match_id)
            if m is None:
                raise KeyError(match_id)
            a, b = db.get(SourceRecord, m.a_id), db.get(SourceRecord, m.b_id)

            if req.action is s.DecisionAction.REQUEST_INFO:
                return self._request_info(db, m, a, b, req)

            if req.action is s.DecisionAction.REJECT:
                self._cannot_link(db, m, "reviewer rejected the proposed relationship")
                m.review_state = "rejected"
                self._event(db, m, req, "reject", {"verdict": m.verdict})
                return s.DecisionResult(
                    match_id=m.id, new_state=s.ReviewState.REJECTED, verdict=s.Verdict(m.verdict),
                    message="Recorded as a cannot-link constraint. These will never be merged, "
                            "and the pair will not be proposed again.")

            # approve
            if m.verdict == GateVerdict.INSUFFICIENT_EVIDENCE.value:
                raise ValueError(
                    "This pair cannot be approved while a critical attribute is unknown. "
                    "Use request_info and supply the missing value.")

            if m.verdict == GateVerdict.DIFFERENT.value:
                self._cannot_link(db, m, "reviewer confirmed these are different materials")
                m.review_state = "approved"
                self._event(db, m, req, "approve_different", {})
                return s.DecisionResult(
                    match_id=m.id, new_state=s.ReviewState.APPROVED, verdict=s.Verdict(m.verdict),
                    message="Confirmed as different materials. Recorded as a cannot-link constraint.")

            if m.verdict == GateVerdict.POSSIBLE_ALTERNATIVE.value:
                condition = next((f["message"] for f in (m.gate_firings or [])
                                  if f.get("gate_id") == "_conditions"), "")
                if not db.scalar(select(PossibleAlternative).where(
                        PossibleAlternative.a_id == m.a_id, PossibleAlternative.b_id == m.b_id)):
                    db.add(PossibleAlternative(a_id=m.a_id, b_id=m.b_id, condition=condition))
                m.review_state = "approved"
                self._event(db, m, req, "approve_alternative", {"condition": condition})
                return s.DecisionResult(
                    match_id=m.id, new_state=s.ReviewState.APPROVED, verdict=s.Verdict(m.verdict),
                    message="Linked as a conditional substitute. Identities stay separate and "
                            "both source codes are unchanged.")

            canonical_id = self._merge(db, a, b, req.reviewer)
            m.review_state = "approved"
            self._event(db, m, req, "approve_same", {"canonical_id": canonical_id})
            return s.DecisionResult(
                match_id=m.id, new_state=s.ReviewState.APPROVED, canonical_id=canonical_id,
                verdict=s.Verdict(m.verdict),
                message=f"Mapped to {canonical_id}. Both source codes are retained and unchanged.")

    # -- internals -----------------------------------------------------------
    def _request_info(self, db, m, a, b, req) -> s.DecisionResult:
        """A reviewer answers the question the system asked, and the pair is re-decided.

        The supplied value is stored with method `given`, so the audit trail distinguishes
        what a machine read from what a person asserted.
        """
        applied = []
        for key, value in (req.provided_attributes or {}).items():
            target = a if any(x.key == key and x.status == "unknown" for x in a.attributes) else b
            row = next((x for x in target.attributes if x.key == key), None)
            if row is None:
                continue
            family = self.dictionary.family(target.family)
            defn = family.attribute(key)
            if defn and defn.type == "number":
                try:
                    row.value_number, row.value_text = float(value), None
                except ValueError:
                    continue
            else:
                row.value_text, row.value_number = str(value), None
            row.status, row.method = "extracted", "given"
            row.evidence = f"supplied by {req.reviewer}"
            row.confidence = 1.0
            applied.append(f"{target.source_code}.{key}={value}")

        db.flush()
        if applied:
            family = self.dictionary.family(a.family)
            result = cascade.run(family, a.attrs(), b.attrs())
            m.verdict, m.decided_by, m.score = result.verdict.value, result.decided_by, result.score
            m.rationale, m.gate_overrode = result.rationale, result.gate_overrode
            m.review_state = "queued"
            self._event(db, m, req, "information_supplied",
                        {"applied": applied, "new_verdict": m.verdict})
            return s.DecisionResult(
                match_id=m.id, new_state=s.ReviewState.QUEUED, verdict=s.Verdict(m.verdict),
                message=f"Recorded {', '.join(applied)}. Re-evaluated as {m.verdict}.")

        m.review_state = "info_requested"
        self._event(db, m, req, "information_requested", {"note": req.note})
        return s.DecisionResult(
            match_id=m.id, new_state=s.ReviewState.INFO_REQUESTED, verdict=s.Verdict(m.verdict),
            message="Information requested. The pair returns to the queue when answered.")

    def _cannot_link(self, db, m, reason: str) -> None:
        if not db.scalar(select(KnownConflict).where(
                KnownConflict.a_id == m.a_id, KnownConflict.b_id == m.b_id)):
            db.add(KnownConflict(a_id=m.a_id, b_id=m.b_id, reason=reason, source="reviewer"))

    def _merge(self, db, a: SourceRecord, b: SourceRecord, reviewer: str) -> str:
        """Attach both records to one canonical identity, creating it if needed."""
        existing = [
            db.scalar(select(ApprovedMapping).where(ApprovedMapping.record_id == r.id))
            for r in (a, b)
        ]
        canonical_id = next((m.canonical_id for m in existing if m), None)
        if canonical_id is None:
            canonical_id = registry.next_id(db)
            db.add(CanonicalMaterial(canonical_id=canonical_id, family=a.family))
            db.flush()

        for record, mapping in zip((a, b), existing):
            if mapping is None:
                db.add(ApprovedMapping(canonical_id=canonical_id, record_id=record.id,
                                       approved_by=reviewer))
        db.flush()
        self._restate(db, canonical_id)
        return canonical_id

    def _restate(self, db, canonical_id: str) -> None:
        """Rebuild the canonical description from every mapped record.

        Survivorship deliberately does NOT pick a winning record. The description is
        synthesised from the union of evidenced attributes, so a merge never silently
        discards a fact one source had and another lacked. Where two sources disagree on a
        non-blocking attribute, the value seen most often wins and the alternatives are
        retained on the canonical record.
        """
        canonical = db.get(CanonicalMaterial, canonical_id)
        record_ids = list(db.scalars(select(ApprovedMapping.record_id)
                                     .where(ApprovedMapping.canonical_id == canonical_id)))
        records = [db.get(SourceRecord, rid) for rid in record_ids]
        if not records:
            return
        family = self.dictionary.family(records[0].family)

        tally: dict[str, dict[str, int]] = {}
        for r in records:
            for k, v in r.attrs().items():
                tally.setdefault(k, {}).setdefault(str(v), 0)
                tally[k][str(v)] += 1

        merged = {k: max(vals.items(), key=lambda kv: kv[1])[0] for k, vals in tally.items()}
        conflicts = {k: sorted(vals) for k, vals in tally.items() if len(vals) > 1}

        def fmt(key: str) -> str:
            v = merged.get(key)
            if v is None:
                return ""
            try:
                return f"{float(v):g}"
            except (TypeError, ValueError):
                return str(v)

        fields = {a.key: fmt(a.key) for a in family.attributes}
        try:
            canonical.standardised_short = family.naming.short_template.format(
                noun=family.naming.noun, modifier=family.naming.modifier, **fields
            ).replace("; ;", ";").strip("; ")
            canonical.standardised_long = family.naming.long_template.format(
                noun=family.naming.noun, modifier=family.naming.modifier, **fields
            ).strip()
        except (KeyError, IndexError):
            canonical.standardised_short = " ".join(
                [family.naming.noun, family.naming.modifier] + [v for v in fields.values() if v])
        canonical.attributes = {"merged": merged, "conflicting": conflicts,
                                "sources": [r.source_code for r in records]}

    def _event(self, db, m, req, action: str, payload: dict) -> None:
        db.add(DecisionEvent(
            pair_id=m.id, canonical_id=payload.get("canonical_id"), actor=req.reviewer,
            action=action, payload={**payload, "note": req.note, "verdict": m.verdict}))


# ---------------------------------------------------------------------------
# Questions: the queue as a person actually experiences it
# ---------------------------------------------------------------------------
class LiveQuestions:
    """Turns deferred pairs into a ranked list of blanks to fill.

    The review queue holds pairs, but a reviewer does not answer pairs. One record appears
    in many blocked pairs, and a single answer clears every one of them. Measured on the
    generated catalogue, 689 deferred pairs are 228 blanks across 207 records, and answering
    the fifty highest-value blanks clears half the queue.

    Ranking by how many pairs an answer unblocks turns an undifferentiated wall of
    comparisons into a worklist with the most valuable question at the top.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def _blanks(self, db) -> tuple[dict, int]:
        """Map (record_id, attribute) -> the deferred pairs it blocks."""
        pending = list(db.scalars(
            select(CandidateMatch).where(
                CandidateMatch.review_state == "queued",
                CandidateMatch.verdict == GateVerdict.INSUFFICIENT_EVIDENCE.value)))
        ids = {i for m in pending for i in (m.a_id, m.b_id)}
        recs = {
            r.id: r for r in db.scalars(
                select(SourceRecord).where(SourceRecord.id.in_(ids))
                .options(selectinload(SourceRecord.attributes)))
        } if ids else {}

        blanks: dict[tuple[int, str], dict] = {}
        for m in pending:
            a, b = recs.get(m.a_id), recs.get(m.b_id)
            if a is None or b is None:
                continue
            family = self.dictionary.family(a.family)
            aa, ab = a.attrs(), b.attrs()
            _, _, _, missing, _ = cascade.attribute_agreement(family, aa, ab)
            for key in missing:
                silent, other = (a, ab) if key not in aa else (b, aa)
                entry = blanks.setdefault((silent.id, key), {"pairs": set(), "counterpart": Counter()})
                entry["pairs"].add(m.id)
                if other.get(key) is not None:
                    entry["counterpart"][str(other[key])] += 1
        return blanks, len(pending)

    def questions(self, cursor: str | None, limit: int) -> s.QuestionPage:
        with session_scope() as db:
            blanks, deferred = self._blanks(db)

            per_record: dict[int, list] = {}
            for (record_id, key), info in blanks.items():
                per_record.setdefault(record_id, []).append((key, info))

            items: list[s.Question] = []
            for record_id, fields in per_record.items():
                r = db.get(SourceRecord, record_id)
                family = self.dictionary.family(r.family)
                blocked = set()
                missing = []
                for key, info in sorted(fields, key=lambda f: -len(f[1]["pairs"])):
                    defn = family.attribute(key)
                    blocked |= info["pairs"]
                    missing.append(s.MissingField(
                        key=key, label=defn.label if defn else key,
                        criticality=defn.criticality.value if defn else "critical",
                        pairs_blocked=len(info["pairs"]),
                        counterpart_values=[
                            s.CounterpartValue(value=v, seen_on=n)
                            for v, n in info["counterpart"].most_common(4)],
                    ))
                items.append(s.Question(
                    record_id=r.id, org_code=r.org.code, source_code=r.source_code,
                    raw_description=r.raw_description, missing=missing,
                    pairs_blocked=len(blocked)))

            items.sort(key=lambda q: -q.pairs_blocked)

            ordered = sorted(blanks.values(), key=lambda i: -len(i["pairs"]))
            curve, seen = [], set()
            for n, info in enumerate(ordered, start=1):
                seen |= info["pairs"]
                if n in (10, 25, 50, 100, 200, len(ordered)):
                    curve.append(s.CurvePoint(
                        questions_answered=n, pairs_cleared=len(seen),
                        share_cleared=round(len(seen) / deferred, 4) if deferred else 0.0))

            offset = int(cursor) if cursor and cursor.isdigit() else 0
            page = items[offset:offset + limit]
            return s.QuestionPage(
                pairs_deferred=deferred, questions=len(blanks), records=len(per_record),
                curve=curve, items=page,
                next_cursor=str(offset + limit) if offset + limit < len(items) else None)

    def unresolvable(self, record_id: int, req: s.UnresolvableRequest) -> s.AnswerResult:
        """A person looked and the answer does not exist. Stop asking.

        Without this a review queue is permanent: every run re-proposes the same pair and
        re-asks the same unanswerable question. Marking it settled lets those pairs reach a
        final state, which is separate identities where the other side states a
        conflict-critical fact.
        """
        with session_scope() as db:
            record = db.get(SourceRecord, record_id)
            if record is None:
                raise KeyError(record_id)
            family = self.dictionary.family(record.family)
            by_key = {a.key: a for a in record.attributes}
            marked = {}
            for key in req.keys:
                row = by_key.get(key)
                if row is None:
                    continue
                row.status, row.method = "unresolvable", "given"
                row.evidence = f"{req.reviewer}: {req.reason}" if req.reason else f"declared unobtainable by {req.reviewer}"
                marked[key] = "unresolvable"
            if not marked:
                return s.AnswerResult(record_id=record_id, applied={}, pairs_reevaluated=0,
                                      message="No recognised attribute was named.")
            db.flush()
            affected = list(db.scalars(select(CandidateMatch).where(
                CandidateMatch.review_state == "queued",
                (CandidateMatch.a_id == record_id) | (CandidateMatch.b_id == record_id))))
            resolved = s.QueueCounts()
            for m in affected:
                a, b = db.get(SourceRecord, m.a_id), db.get(SourceRecord, m.b_id)
                r = cascade.run(family, a.attrs(), b.attrs(), a.unresolvable(), b.unresolvable())
                m.verdict, m.decided_by, m.score = r.verdict.value, r.decided_by, r.score
                m.rationale, m.gate_overrode = r.rationale, r.gate_overrode
                setattr(resolved, _GROUP_OF[m.verdict], getattr(resolved, _GROUP_OF[m.verdict]) + 1)
            db.add(DecisionEvent(actor=req.reviewer, action="declared_unresolvable",
                                 payload={"record_id": record_id, "keys": list(marked),
                                          "reason": req.reason}))
            return s.AnswerResult(
                record_id=record_id, applied=marked, pairs_reevaluated=len(affected),
                resolved=resolved,
                message=f"{', '.join(marked)} recorded as unobtainable on {record.source_code}. "
                        f"{len(affected)} pairs re-decided and will not be asked about again.")

    def answer(self, record_id: int, req: s.AnswerRequest) -> s.AnswerResult:
        """Fill in the blanks on one record and re-decide every pair it was blocking."""
        with session_scope() as db:
            record = db.get(SourceRecord, record_id)
            if record is None:
                raise KeyError(record_id)
            family = self.dictionary.family(record.family)
            by_key = {a.key: a for a in record.attributes}

            applied: dict[str, str] = {}
            for key, value in req.values.items():
                row, defn = by_key.get(key), family.attribute(key)
                if row is None or defn is None:
                    continue
                if defn.type == "number":
                    try:
                        row.value_number, row.value_text = float(value), None
                    except ValueError:
                        continue
                else:
                    canonical = value
                    if defn.values:
                        from samepart.pipeline.extract import _match_enum
                        canonical = _match_enum(defn, value) or value
                    row.value_text, row.value_number = str(canonical), None
                row.status, row.method = "extracted", "given"
                row.evidence = f"supplied by {req.reviewer}"
                row.confidence = 1.0
                applied[key] = str(row.value_text or row.value_number)

            if not applied:
                return s.AnswerResult(record_id=record_id, applied={}, pairs_reevaluated=0,
                                      message="No recognised attribute was supplied.")
            db.flush()

            affected = list(db.scalars(select(CandidateMatch).where(
                CandidateMatch.review_state == "queued",
                (CandidateMatch.a_id == record_id) | (CandidateMatch.b_id == record_id))))
            resolved = s.QueueCounts()
            for m in affected:
                a, b = db.get(SourceRecord, m.a_id), db.get(SourceRecord, m.b_id)
                result = cascade.run(family, a.attrs(), b.attrs())
                m.verdict, m.decided_by, m.score = result.verdict.value, result.decided_by, result.score
                m.rationale, m.gate_overrode = result.rationale, result.gate_overrode
                setattr(resolved, _GROUP_OF[m.verdict],
                        getattr(resolved, _GROUP_OF[m.verdict]) + 1)

            db.add(DecisionEvent(actor=req.reviewer, action="attributes_supplied",
                                 payload={"record_id": record_id, "applied": applied,
                                          "pairs_reevaluated": len(affected),
                                          "note": req.note}))
            return s.AnswerResult(
                record_id=record_id, applied=applied, pairs_reevaluated=len(affected),
                resolved=resolved,
                message=f"Recorded {', '.join(f'{k}={v}' for k, v in applied.items())} on "
                        f"{record.source_code}. {len(affected)} blocked pairs re-decided.")
