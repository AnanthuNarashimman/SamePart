"""Live service implementations, backed by the database and the pipeline.

Each class satisfies one protocol in `protocols.py` and is selected in `api/deps.py`. They
are added one at a time; anything not yet implemented stays on its stub, and the frontend
cannot tell the difference.
"""
from __future__ import annotations

import os
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from samepart import audit
from samepart.api import schemas as s
from samepart.db.models import (ExtractedAttribute, Organisation, ProcurementLine,
                                SourceRecord)
from samepart.config import settings
from samepart.db.session import session_scope
from samepart.dictionary.loader import Dictionary
from samepart.ingest.csv_loader import Row, load_csv
from samepart.ingest.procurement_loader import load_procurement_csv
from samepart.pipeline.extract import extract

# Import status is held in memory. Ingestion is synchronous and fast at this scale; when it
# becomes a background job this moves to a table.
_IMPORTS: dict[str, s.ImportStatus] = {}

_GIVEN_KEYS = ("manufacturer", "manufacturer_part_number")


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip())
    except ValueError:
        return None


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
        new_ids: set[int] = set()
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
            skipped: list[str] = []
            for row in result.rows:
                if row.source_code in existing:
                    skipped.append(row.source_code)
                    continue
                existing.add(row.source_code)
                record = self._persist(db, org.id, family.family, row)
                new_ids.add(record.id)
                ingested += 1
                attributes += self._extract_into(db, record, row)

        status.rows_ingested = ingested
        status.rows_skipped = len(skipped)
        status.attributes_extracted = attributes

        # A file imported against the wrong family is silent: the family's patterns match
        # nothing, every row lands with no attributes, and the import reports success. The
        # request carries a default family, so this is easy to do by accident from the UI.
        if ingested and attributes / ingested < 0.5 and len(self.dictionary.families) > 1:
            status.warnings.append(
                f"Only {attributes} attributes were read from {ingested} rows as "
                f"'{family.family}'. If these are not {family.label.lower()}, re-import under "
                f"the right family: {', '.join(sorted(self.dictionary.families))}.")

        # Matching runs immediately, scoped to what just arrived, so an import is visible in
        # the queue without a separate manual step.
        if new_ids:
            found = LiveReview(self.dictionary).build_matches(
                family_name=family.family, only_records=new_ids)
            status.candidate_pairs = found["candidate_pairs"]
            status.auto_merged = found["auto_merged"]
            status.queued_for_review = sum(
                n for g, n in found["by_group"].items() if g != "different")
            status.matched_at = datetime.now(timezone.utc)
        status.status = "completed"
        if skipped:
            shown = ", ".join(skipped[:5]) + ("…" if len(skipped) > 5 else "")
            status.warnings.append(
                f"{len(skipped)} of {result.rows_read} rows were already imported for "
                f"{req.org_code} and were skipped ({shown}). Re-importing the same file is "
                f"safe and changes nothing.")
        _IMPORTS[import_id] = status
        return status

    def import_procurement(self, org_code: str, content: bytes,
                           column_map: dict | None = None) -> s.ImportStatus:
        """Ingest a CPSE purchase order extract and link each line to its material record."""
        import_id = str(uuid.uuid4())[:8]
        result = load_procurement_csv(content, self.dictionary.units, column_map)
        status = s.ImportStatus(
            import_id=import_id, org_code=org_code, status="running",
            rows_read=result.rows_read, errors=list(result.errors[:50]),
            started_at=datetime.now(timezone.utc))
        if not result.rows:
            status.status = "failed"
            _IMPORTS[import_id] = status
            return status

        ingested = unlinked = 0
        with session_scope() as db:
            org = db.scalar(select(Organisation).where(Organisation.code == org_code))
            if org is None:
                status.status = "failed"
                status.errors.append(f"unknown organisation {org_code}; import the catalogue first")
                _IMPORTS[import_id] = status
                return status

            record_ids = {
                code: rid for code, rid in db.execute(
                    select(SourceRecord.source_code, SourceRecord.id)
                    .where(SourceRecord.org_id == org.id)).all()
            }
            seen = set(db.execute(
                select(ProcurementLine.po_number, ProcurementLine.line_no)
                .where(ProcurementLine.org_id == org.id)).all())

            for row in result.rows:
                if (row.po_number, row.line_no) in seen:
                    continue
                seen.add((row.po_number, row.line_no))
                rid = record_ids.get(row.source_code)
                if rid is None:
                    unlinked += 1
                db.add(ProcurementLine(
                    org_id=org.id, record_id=rid, source_code=row.source_code,
                    po_number=row.po_number, line_no=row.line_no,
                    po_date=datetime.combine(row.po_date, datetime.min.time()),
                    vendor=row.vendor, vendor_part_number=row.vendor_part_number,
                    plant=row.plant, quantity=row.quantity, uom=row.uom,
                    base_quantity=row.base_quantity, base_uom=row.base_uom,
                    unit_price=row.unit_price, unit_price_base=row.unit_price_base,
                    line_value=row.line_value, currency=row.currency))
                ingested += 1

        if unlinked:
            status.warnings.append(
                f"{unlinked} lines reference a source code not in the material master; "
                f"kept for spend analysis but not linked to a record")
        status.status = "completed"
        status.rows_ingested = ingested
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
            stock_on_hand=row.stock_on_hand, stock_base_qty=row.stock_base_qty,
            last_issue_date=_parse_date(row.last_issue_date),
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
    def build_matches(self, family_name: str, verbose: bool = False,
                      only_records: set[int] | None = None) -> dict:
        """Retrieve candidates, run the cascade, persist a verdict for every pair.

        Idempotent: existing rows are refreshed rather than duplicated, and any pair a human
        has already decided is left alone.

        `only_records` scopes the work to pairs involving those records, which is what an
        import needs. Newly arrived records still compare against the whole corpus, but the
        thousands of pairs that were already decided are not recomputed. This is also how it
        would run in production: a full rebuild is a migration, not a daily operation.
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

            # The model tier is opt-in for matching, off by default. It costs about two
            # seconds a pair and only the genuinely ambiguous band reaches it, but on a full
            # rebuild that band is still large enough to matter. Same posture as egress:
            # the safe thing runs unless someone deliberately asks for the other.
            model = None
            if os.getenv("SAMEPART_MODEL_MATCHING", "0").lower() in ("1", "true", "yes"):
                from samepart.model.client import get_model
                candidate = get_model()
                model = candidate if candidate.available else None

            pairs = retriever.candidate_pairs()
            if only_records:
                pairs = {p for p in pairs
                         if int(p[0]) in only_records or int(p[1]) in only_records}

            for sa, sb in pairs:
                a_id, b_id = sorted((int(sa), int(sb)))
                a, b = by_id[a_id], by_id[b_id]
                result = cascade.run(family, a.attrs(), b.attrs(),
                                     a.unresolvable(), b.unresolvable(), model=model)
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

        return {"records": stats.records,
                "candidate_pairs": len(pairs) if only_records else stats.candidate_pairs,
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

            # Approving a pair that spans organisations is the moment a national identifier
            # comes into existence, and that is not a decision one CPSE makes about another's
            # codes. Answering a question is not an approval and is not gated.
            if req.action is not s.DecisionAction.REQUEST_INFO:
                ruling = gov.may_decide(req.reviewer_role,
                                        {a.org.code, b.org.code}, req.reviewer_org)
                if not ruling.allowed:
                    raise PermissionError(
                        f"{ruling.reason} Required role: {ruling.required_role}.")

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

        # Classification. The family's declared anchor wins outright: once extraction has
        # decided this is a hex bolt, its class is known rather than inferred.
        anchor = family.classification.code
        if anchor:
            canonical.classification_code = anchor

    def _event(self, db, m, req, action: str, payload: dict) -> None:
        audit.record(
            db, pair_id=m.id, canonical_id=payload.get("canonical_id"), actor=req.reviewer,
            action=action, payload={**payload, "note": req.note, "verdict": m.verdict})


class ModelEnrichment:
    """Second-pass extraction for attributes the patterns could not read.

    Deliberately NOT inline with ingestion. A model call takes around two seconds, so
    enriching 654 records would add twenty minutes to an import that currently takes under
    one. It runs as its own pass, over only the records that have blanks, and only where the
    text might plausibly contain the answer.

    Anything it fills is stored with method `llm` and its quoted evidence, so a reviewer can
    always see that a machine inferred this rather than a pattern reading it outright.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def enrich(self, family_name: str | None = None, limit: int | None = None) -> dict:
        """Second-pass extraction over every family, or one named family.

        The default was the literal "hex_bolt", so with four families loaded three quarters of
        the records carrying blanks were never offered to the model at all — silently, because
        an unenriched record looks exactly like one the model declined to fill.
        """
        if family_name is None:
            totals: dict = {"families": {}}
            for name in sorted(self.dictionary.families):
                totals["families"][name] = self.enrich(name, limit=limit)
            return totals
        return self._enrich_one(family_name, limit)

    def _enrich_one(self, family_name: str, limit: int | None = None) -> dict:
        from samepart.model.client import get_model
        from samepart.model.extract import extract_missing
        from samepart.pipeline.extract import extract as regex_extract

        model = get_model()
        if not model.available:
            return {"model": model.name, "available": False,
                    "note": "no model configured; nothing was changed"}

        family = self.dictionary.family(family_name)
        filled = abstained = rejected = considered = touched = 0
        errors = 0

        with session_scope() as db:
            records = list(db.scalars(
                select(SourceRecord).where(SourceRecord.family == family_name)
                .options(selectinload(SourceRecord.attributes))))
            targets = [r for r in records
                       if any(a.status == "unknown" for a in r.attributes)]
            if limit:
                targets = targets[:limit]

            for record in targets:
                current = regex_extract(family, record.raw_description)
                for a in record.attributes:
                    if a.key in current and a.status != "unknown":
                        continue
                result = extract_missing(model, family, record.raw_description, current)
                if result.error and not result.values:
                    errors += 1
                    continue
                considered += result.filled + result.abstained + result.rejected
                abstained += result.abstained
                rejected += result.rejected
                if not result.values:
                    continue
                touched += 1
                by_key = {a.key: a for a in record.attributes}
                for key, value in result.values.items():
                    row = by_key.get(key)
                    if row is None:
                        continue
                    if isinstance(value.value, (int, float)):
                        row.value_number, row.value_text = float(value.value), None
                    else:
                        row.value_text, row.value_number = str(value.value), None
                    row.status, row.method = "extracted", "llm"
                    row.evidence, row.confidence = value.evidence, value.confidence
                    filled += 1

        return {"model": model.name, "available": True, "records_examined": len(targets),
                "records_changed": touched, "attributes_considered": considered,
                "filled": filled, "abstained": abstained,
                "rejected_no_evidence": rejected, "errors": errors}


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
            # The whole curve, not a handful of checkpoints. The loop already visits every
            # answer, so the samples were free to take and expensive to omit: with checkpoints
            # at 10/25/50/100 the first one past half the queue was 50 answers, which actually
            # clears 74%, and the caption under the chart read "50 answers clear half the
            # queue" — overstating the effort by roughly double. A dense curve also lets the
            # chart use a real numeric axis, so the diminishing-returns bend is drawn to scale
            # instead of being flattened by equal category spacing.
            #
            # Strided once the queue is long, so the payload stays bounded on a real catalogue.
            stride = max(1, len(ordered) // 240)
            curve, seen = [], set()
            for n, info in enumerate(ordered, start=1):
                seen |= info["pairs"]
                if n % stride == 0 or n == len(ordered):
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
            audit.record(db, actor=req.reviewer, action="declared_unresolvable",
                         payload={"record_id": record_id, "keys": list(marked),
                                  "reason": req.reason})
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

            audit.record(db, actor=req.reviewer, action="attributes_supplied",
                         payload={"record_id": record_id, "applied": applied,
                                  "pairs_reevaluated": len(affected),
                                  "note": req.note})
            return s.AnswerResult(
                record_id=record_id, applied=applied, pairs_reevaluated=len(affected),
                resolved=resolved,
                message=f"Recorded {', '.join(f'{k}={v}' for k, v in applied.items())} on "
                        f"{record.source_code}. {len(affected)} blocked pairs re-decided.")


# ---------------------------------------------------------------------------
# Analytics: what the harmonisation is actually worth
# ---------------------------------------------------------------------------
import statistics  # noqa: E402

from samepart.db.models import ProcurementLine as PO  # noqa: E402

WINDOW_LABEL = "last 4 financial years"


class LiveAnalytics:
    """Read-only aggregation over decisions already made and orders already placed.

    Every price here is per base unit. That is the whole reason unit normalisation happens
    at ingestion: a purchase of one box of a hundred and a purchase of a hundred each are
    the same purchase, and comparing them unnormalised produces a hundredfold error in a
    number a judge will read off a slide.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    # -- summary ------------------------------------------------------------
    def summary(self) -> s.AnalyticsSummary:
        with session_scope() as db:
            records = db.scalar(select(func.count(SourceRecord.id))) or 0
            canon = db.scalar(select(func.count(CanonicalMaterial.canonical_id))) or 0
            mapped = db.scalar(select(func.count(ApprovedMapping.id))) or 0
            conflicts = db.scalar(select(func.count(KnownConflict.id))) or 0
            lines = db.scalar(select(func.count(PO.id))) or 0
            spend = db.scalar(select(func.sum(PO.line_value))) or 0.0

            counts = s.QueueCounts()
            for verdict, n in db.execute(
                select(CandidateMatch.verdict, func.count(CandidateMatch.id))
                .where(CandidateMatch.review_state == "queued")
                .group_by(CandidateMatch.verdict)
            ).all():
                setattr(counts, _GROUP_OF[verdict], n)

            ordered = {c for (c,) in db.execute(select(PO.source_code).distinct())}
            dead_by_org: dict[str, int] = {}
            per_org: list[s.OrgDuplicateStat] = []
            for org in db.scalars(select(Organisation).order_by(Organisation.code)):
                codes = [c for (c,) in db.execute(
                    select(SourceRecord.source_code).where(SourceRecord.org_id == org.id))]
                org_mapped = db.scalar(
                    select(func.count(ApprovedMapping.id))
                    .join(SourceRecord, SourceRecord.id == ApprovedMapping.record_id)
                    .where(SourceRecord.org_id == org.id)) or 0
                dead = sum(1 for c in codes if c not in ordered)
                dead_by_org[org.code] = dead
                per_org.append(s.OrgDuplicateStat(
                    org_code=org.code, records=len(codes), mapped_to_canonical=org_mapped,
                    duplicate_rate=round(org_mapped / len(codes), 4) if codes else 0.0,
                    dead_codes=dead))

            shared = 0
            for _, n in db.execute(
                select(ApprovedMapping.canonical_id,
                       func.count(func.distinct(SourceRecord.org_id)))
                .join(SourceRecord, SourceRecord.id == ApprovedMapping.record_id)
                .group_by(ApprovedMapping.canonical_id)).all():
                if n > 1:
                    shared += 1

            dead = sum(dead_by_org.values())
            # A source code that has merged into a canonical identity shared with another
            # record is, by definition, a duplicate of something.
            duplicates = max(mapped - canon, 0)
            return s.AnalyticsSummary(
                records=records, canonical_materials=canon, merged=mapped,
                conflicts_caught=conflicts,
                duplicate_rate=round(duplicates / records, 4) if records else 0.0,
                queue_by_group=counts, procurement_lines=lines,
                total_spend=round(spend, 2), spend_window=WINDOW_LABEL,
                dead_codes=dead,
                dead_code_rate=round(dead / records, 4) if records else 0.0,
                shared_materials=shared, by_org=per_org)

    # -- the money ----------------------------------------------------------
    def _clusters(self, db):
        """Per canonical material: which CPSEs buy it, at what unit prices, and how much."""
        rows = db.execute(
            select(ApprovedMapping.canonical_id, Organisation.code, SourceRecord.source_code,
                   PO.unit_price_base, PO.base_quantity, PO.line_value)
            .join(SourceRecord, SourceRecord.id == ApprovedMapping.record_id)
            .join(Organisation, Organisation.id == SourceRecord.org_id)
            .join(PO, PO.record_id == SourceRecord.id)
            .where(PO.unit_price_base.is_not(None))).all()

        out: dict[str, dict] = {}
        for cid, org, code, price, qty, value in rows:
            c = out.setdefault(cid, {"orgs": set(), "codes": set(), "prices": [],
                                     "qty": 0.0, "spend": 0.0, "lines": 0})
            c["orgs"].add(org)
            c["codes"].add(code)
            c["prices"].append(price)
            c["qty"] += qty or 0.0
            c["spend"] += value or 0.0
            c["lines"] += 1
        return out

    def savings(self) -> s.SavingsResult:
        # Money is only claimed on merges we are confident in. A flagged cluster may be two
        # different materials, and its price gap would then be an artefact of our own error
        # rather than a procurement saving. Excluded from the headline, reported separately.
        flagged = {f.canonical_id for f in self.audit_flags(limit=10_000).items}

        with session_scope() as db:
            clusters = self._clusters(db)
            names = dict(db.execute(
                select(CanonicalMaterial.canonical_id,
                       CanonicalMaterial.standardised_short)).all())
            classes = dict(db.execute(
                select(CanonicalMaterial.canonical_id,
                       CanonicalMaterial.classification_code)).all())

            items: list[s.SavingsCluster] = []
            excluded_n = 0
            excluded_value = 0.0
            for cid, c in clusters.items():
                if len(c["orgs"]) < 2:
                    continue          # aggregation needs more than one buyer
                if cid in flagged:
                    lo = min(c["prices"])
                    excluded_n += 1
                    excluded_value += max(c["spend"] - lo * c["qty"], 0.0)
                    continue
                lo, hi = min(c["prices"]), max(c["prices"])
                # What the same volume would have cost at the best price anyone achieved.
                opportunity = max(c["spend"] - lo * c["qty"], 0.0)
                items.append(s.SavingsCluster(
                    canonical_id=cid,
                    national_code=registry.national_code(cid, classes.get(cid)),
                    standardised_short=names.get(cid) or cid,
                    orgs=sorted(c["orgs"]), price_min=round(lo, 2), price_max=round(hi, 2),
                    spread_pct=round((hi / lo - 1) * 100, 1) if lo else 0.0,
                    total_quantity=round(c["qty"], 2), total_spend=round(c["spend"], 2),
                    po_lines=c["lines"], aggregation_opportunity=round(opportunity, 2)))

            items.sort(key=lambda i: -i.aggregation_opportunity)
            return s.SavingsResult(
                total_opportunity=round(sum(i.aggregation_opportunity for i in items), 2),
                total_spend=round(sum(i.total_spend for i in items), 2),
                shared_materials=len(items), window=WINDOW_LABEL,
                excluded_flagged_clusters=excluded_n,
                excluded_opportunity=round(excluded_value, 2),
                clusters=items[:50])

    # -- capability 5 -------------------------------------------------------
    def rationalisation(self, limit: int = 100) -> s.RationalisationResult:
        with session_scope() as db:
            last_po = dict(db.execute(
                select(PO.source_code, func.max(PO.po_date)).group_by(PO.source_code)).all())
            mapping = dict(db.execute(
                select(ApprovedMapping.record_id, ApprovedMapping.canonical_id)).all())
            canon_size: dict[str, int] = {}
            for cid, n in db.execute(
                select(ApprovedMapping.canonical_id, func.count(ApprovedMapping.id))
                .group_by(ApprovedMapping.canonical_id)).all():
                canon_size[cid] = n

            records = list(db.scalars(select(SourceRecord)))
            dead: list[s.DeadCode] = []
            for r in records:
                if r.source_code in last_po:
                    continue
                dead.append(s.DeadCode(
                    record_id=r.id, org_code=r.org.code, source_code=r.source_code,
                    raw_description=r.raw_description,
                    canonical_id=mapping.get(r.id), last_purchase=None))

            # Codes that are duplicates of another and could collapse into it.
            removable = sum(max(n - 1, 0) for n in canon_size.values())
            total = len(records)
            return s.RationalisationResult(
                window=WINDOW_LABEL, records=total, dead_codes=len(dead),
                dead_code_rate=round(len(dead) / total, 4) if total else 0.0,
                duplicate_codes_removable=removable,
                items=sorted(dead, key=lambda d: (d.org_code, d.source_code))[:limit])

    # -- the system flags its own suspicious merges -------------------------
    def audit_flags(self, limit: int = 50) -> s.AuditFlagResult:
        with session_scope() as db:
            clusters = self._clusters(db)
            names = dict(db.execute(
                select(CanonicalMaterial.canonical_id,
                       CanonicalMaterial.standardised_short)).all())

            spreads = {cid: (max(c["prices"]) / min(c["prices"]))
                       for cid, c in clusters.items()
                       if len(c["prices"]) > 1 and min(c["prices"]) > 0}
            if not spreads:
                return s.AuditFlagResult(median_spread_all=0.0, threshold=0.0, flagged=0)

            median = statistics.median(spreads.values())
            threshold = round(median * 1.5, 3)

            items = [
                s.AuditFlag(
                    canonical_id=cid,
                    standardised_short=names.get(cid),
                    reason=(f"Unit price varies {spread:.1f}x across buyers, against a median "
                            f"of {median:.1f}x. Spend data played no part in this merge, so "
                            f"the pattern is independent evidence it may be wrong."),
                    price_spread=round(spread, 2),
                    orgs=sorted(clusters[cid]["orgs"]),
                    source_codes=sorted(clusters[cid]["codes"]))
                for cid, spread in spreads.items() if spread > threshold
            ]
            items.sort(key=lambda i: -i.price_spread)
            return s.AuditFlagResult(
                median_spread_all=round(median, 3), threshold=threshold,
                flagged=len(items), items=items[:limit])


def _taxonomy():
    """Load the classification codeset, or None if it is not present.

    The file is licensed personal-use-only and gitignored, so a checkout legitimately may not
    have it. That is the only failure tolerated here.
    """
    from samepart.taxonomy.loader import Taxonomy

    path = settings.dictionary_dir.parent / "data" / "taxonomy" / "unspsc.xlsx"
    if not path.exists():
        return None
    return Taxonomy.from_xlsx(path)


# ---------------------------------------------------------------------------
# Export: what a CPSE actually loads back into its own system
# ---------------------------------------------------------------------------
class LiveExport:
    """Capabilities 5 and 8: migration support, and integration with the systems of record.

    The shape of the deliverable is the argument. A cross-reference puts the CPSE's own code
    in the first column and never alters it; everything else is additional information about
    that code. Every competing approach in this space merges and deletes inside the
    customer's master, which is why those projects frighten plant teams and stall. This one
    adds rows.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def _context(self, db):
        mapping = dict(db.execute(
            select(ApprovedMapping.record_id, ApprovedMapping.canonical_id)).all())
        approvers = dict(db.execute(
            select(ApprovedMapping.record_id, ApprovedMapping.approved_by)).all())
        approved_at = dict(db.execute(
            select(ApprovedMapping.record_id, ApprovedMapping.at)).all())
        canon = {c.canonical_id: c for c in db.scalars(select(CanonicalMaterial))}
        members: dict[str, list[int]] = {}
        for rid, cid in mapping.items():
            members.setdefault(cid, []).append(rid)
        ordered = {c for (c,) in db.execute(select(PO.source_code).distinct())}
        return mapping, approvers, approved_at, canon, members, ordered

    def cross_reference(self, org_code: str | None = None,
                        limit: int = 5000) -> s.CrossReferenceExport:

        with session_scope() as db:
            mapping, approvers, approved_at, canon, members, ordered = self._context(db)
            q = select(SourceRecord).order_by(SourceRecord.id)
            records = list(db.scalars(q))
            codes = {r.id: r.source_code for r in records}

            # The codeset is licensed and gitignored, so its absence is expected and must
            # not break an export. Only that is caught; anything else is a real fault and a
            # broad except here previously hid one for two features.
            tax = _taxonomy()

            rows: list[s.CrossReferenceRow] = []
            dead = dupes = mapped = 0
            for r in records:
                if org_code and r.org.code != org_code:
                    continue
                cid = mapping.get(r.id)
                material = canon.get(cid) if cid else None
                siblings = [x for x in members.get(cid, []) if x != r.id] if cid else []

                if cid:
                    mapped += 1
                if r.source_code not in ordered:
                    status, dupe = "dead", None
                    dead += 1
                elif siblings:
                    status = "duplicate"
                    dupe = codes.get(sorted(siblings)[0])
                    dupes += 1
                elif cid:
                    status, dupe = "active", None
                else:
                    status, dupe = "unmapped", None

                cls = material.classification_code if material else None
                rows.append(s.CrossReferenceRow(
                    org_code=r.org.code, source_code=r.source_code,
                    national_code=registry.national_code(cid, cls) if cid else None,
                    canonical_identity=cid, classification_code=cls,
                    classification_path=tax.label(cls) if (tax and cls) else None,
                    standardised_short=material.standardised_short if material else None,
                    base_uom=r.base_uom, status=status, duplicate_of=dupe,
                    approved_by=approvers.get(r.id),
                    approved_at=approved_at.get(r.id)))

            return s.CrossReferenceExport(
                generated_at=datetime.now(timezone.utc), rows=len(rows), mapped=mapped,
                dead=dead, duplicates=dupes, items=rows[:limit])

    def migration_plan(self) -> s.MigrationPlan:
        with session_scope() as db:
            mapping, _, _, _, members, ordered = self._context(db)
            records = list(db.scalars(select(SourceRecord)))
            total = len(records)
            close = sum(1 for r in records if r.source_code not in ordered)
            collapse = sum(max(len(v) - 1, 0) for v in members.values())
            keep = len(members)
            review = total - len(mapping)

        return s.MigrationPlan(
            generated_at=datetime.now(timezone.utc), total_codes=total, keep=keep,
            collapse=collapse, close=close, review=review,
            estimated_codes_removed=collapse + close,
            notes=[
                "No CPSE material code is deleted by this plan. Collapsing means the code is "
                "cross-referenced to a national code, not removed from the CPSE's master.",
                "Closing a dead code is a recommendation based on no purchase order in the "
                "window. A stores team confirms it; the system does not act alone.",
                "Codes under review are those the system would not decide without a person.",
            ])

    def passport(self, canonical_id: str) -> s.MaterialPassport:
        """Everything known about one identity, in a record a CPSE can be handed.

        The claim being made is that four organisations independently described the same
        material, so the passport carries the independence: which organisation stated each
        fact, and the exact words it was read from. A number with no basis is what a CPSE is
        being asked to accept everywhere else in this problem space.
        """
        from samepart import audit

        with session_scope() as db:
            material = db.get(CanonicalMaterial, canonical_id)
            if material is None:
                raise KeyError(canonical_id)

            family = self.dictionary.family(material.family)
            labels = {a.key: a.label for a in family.attributes}
            keys = [a.key for a in family.attributes
                    if not a.is_derived and a.criticality.value in ("critical", "major")]

            mappings = list(db.scalars(select(ApprovedMapping)
                                       .where(ApprovedMapping.canonical_id == canonical_id)))
            records = [db.get(SourceRecord, m.record_id) for m in mappings]
            approved = {m.record_id: m for m in mappings}

            sources = [
                s.PassportSource(
                    org_code=r.org.code, source_code=r.source_code,
                    raw_description=r.raw_description, base_uom=r.base_uom,
                    approved_by=approved[r.id].approved_by, approved_at=approved[r.id].at)
                for r in records if r is not None
            ]

            # Per attribute: the value most sources state, who stated it, and who said
            # otherwise. Silence and disagreement are kept apart -- a CPSE that never wrote a
            # value has not contradicted anything.
            evidence: list[s.PassportEvidence] = []
            for key in keys:
                stated: dict[str, str] = {}
                words: dict[str, str] = {}
                for r in records:
                    if r is None:
                        continue
                    attr = next((a for a in r.attributes if a.key == key), None)
                    if attr is None or attr.status in ("unknown", "unresolvable"):
                        continue
                    value = attr.value_text if attr.value_text is not None else (
                        str(attr.value_number) if attr.value_number is not None else None)
                    if value is None:
                        continue
                    stated[r.source_code] = value
                    if attr.evidence:
                        words[r.source_code] = attr.evidence
                if not stated:
                    continue

                tally: dict[str, int] = {}
                for v in stated.values():
                    tally[v] = tally.get(v, 0) + 1
                agreed = max(tally.items(), key=lambda kv: kv[1])[0]
                by_code = {r.source_code: r.org.code for r in records if r is not None}

                evidence.append(s.PassportEvidence(
                    key=key, label=labels.get(key, key), value=agreed,
                    unit=next((a.unit for r in records if r for a in r.attributes
                               if a.key == key and a.unit), None),
                    stated_by=sorted({by_code[c] for c, v in stated.items() if v == agreed}),
                    differs={by_code[c]: v for c, v in stated.items() if v != agreed},
                    evidence=words))

            alt_ids: list[tuple[int, str]] = []
            for r in records:
                if r is None:
                    continue
                for alt in db.scalars(select(PossibleAlternative)):
                    if alt.a_id == r.id:
                        alt_ids.append((alt.b_id, alt.condition or ""))
                    elif alt.b_id == r.id:
                        alt_ids.append((alt.a_id, alt.condition or ""))
            known = {r.id for r in records if r is not None}
            substitutes = []
            for rid, condition in alt_ids:
                if rid in known:
                    continue
                known.add(rid)
                other = db.get(SourceRecord, rid)
                if other is not None:
                    substitutes.append(s.PassportSubstitute(
                        org_code=other.org.code, source_code=other.source_code,
                        raw_description=other.raw_description, condition=condition or None))

            decisions = [
                s.PassportDecision(
                    at=e.at, actor=e.actor, action=e.action,
                    note=(e.payload or {}).get("note"), entry_hash=e.entry_hash)
                for e in db.scalars(select(DecisionEvent)
                                    .where(DecisionEvent.canonical_id == canonical_id)
                                    .order_by(DecisionEvent.id))
            ]

            chain = audit.verify(db)

            return s.MaterialPassport(
                canonical_id=canonical_id,
                national_code=registry.national_code(canonical_id,
                                                     material.classification_code),
                family=material.family,
                classification_code=material.classification_code,
                standardised_short=material.standardised_short,
                standardised_long=material.standardised_long,
                issued_at=datetime.now(timezone.utc),
                sources=sources, evidence=evidence, substitutes=substitutes,
                decisions=decisions,
                audit_chain_intact=chain.intact,
                audit_note=chain.reason or "Decision trail verified at time of issue.")

    def migration_preview(self, org_code: str | None = None) -> s.MigrationPreview:
        """What loading this into a CPSE's master would do, before anyone does it.

        `fields_altered` is zero by construction, not by policy. The cross-reference writes new
        columns beside a CPSE's own code; there is no code path here that issues an update to a
        field the CPSE already owns. Stating it as a count a plant team can check is the whole
        reason they would run this at all.
        """
        data = self.cross_reference(org_code, 50000)

        by_action: dict[str, int] = {}
        sample: list[s.MigrationChange] = []
        for row in data.items:
            action = ("cross_reference" if row.national_code
                      else "review" if row.status != "dead" else "close_recommended")
            by_action[action] = by_action.get(action, 0) + 1
            if len(sample) < 8:
                sample.append(s.MigrationChange(
                    org_code=row.org_code, source_code=row.source_code, action=action,
                    national_code=row.national_code,
                    reason=("cross-referenced to a national identity" if row.national_code
                            else "no decision yet; stays exactly as it is")))

        written = ["national_code", "canonical_identity", "classification_code",
                   "standardised_short", "base_uom", "status", "duplicate_of", "approved_by"]
        read_only = ["org_code", "source_code", "the CPSE's own description",
                     "the CPSE's own unit of measure", "every other field in the master"]

        return s.MigrationPreview(
            org_code=org_code,
            generated_at=datetime.now(timezone.utc),
            codes_in_master=len(data.items),
            rows_added=sum(1 for r in data.items if r.national_code),
            fields_altered=0,
            columns_written=written,
            columns_read_only=read_only,
            by_action=dict(sorted(by_action.items(), key=lambda kv: -kv[1])),
            sample=sample,
            notes=[
                "No existing field is written. The CPSE's own code, description and unit of "
                "measure are read and never updated.",
                "A cross-referenced code is not removed from the master. It gains a national "
                "reference and keeps everything it had.",
                "Codes with no decision yet appear here unchanged, so the preview accounts "
                "for every code rather than only the ones the system acted on.",
            ])

    def erp_payload(self, canonical_id: str) -> dict:
        """A material master payload shaped like the interface an SAP team expects.

        Deliberately mirrors the MATMAS IDoc segment structure: client-level basic data,
        descriptions, and alternative units of measure. Nothing here talks to a real system.
        The point is that the output is in a shape a systems team recognises and can wire up,
        rather than a bespoke format they would have to be talked through.
        """
        with session_scope() as db:
            material = db.get(CanonicalMaterial, canonical_id)
            if material is None:
                raise KeyError(canonical_id)
            record_ids = list(db.scalars(select(ApprovedMapping.record_id)
                                         .where(ApprovedMapping.canonical_id == canonical_id)))
            records = [db.get(SourceRecord, rid) for rid in record_ids]
            attrs = (material.attributes or {}).get("merged", {})

            national = registry.national_code(canonical_id, material.classification_code)
            return {
                "IDOC": {
                    "EDI_DC40": {"IDOCTYP": "MATMAS05", "MESTYP": "MATMAS",
                                 "SNDPRN": "SAMEPART", "RCVPRN": "<CPSE system>"},
                    "E1MARAM": {                       # client-level basic data
                        "MSGFN": "005", "MATNR": national,
                        "MTART": "ERSA", "MBRSH": "M",
                        "MATKL": material.classification_code or "",
                        "MEINS": next((r.base_uom for r in records if r.base_uom), "EA"),
                        "ZZ_NATIONAL_CODE": national,
                        "ZZ_CANONICAL_ID": canonical_id,
                        "E1MAKTM": [                   # descriptions
                            {"MSGFN": "005", "SPRAS_ISO": "EN",
                             "MAKTX": (material.standardised_short or "")[:40]}],
                        "E1MARMM": [                   # alternative units
                            {"MSGFN": "005", "MEINH": r.raw_uom or "EA",
                             "UMREZ": int(r.base_quantity / r.quantity)
                             if r.quantity and r.base_quantity else 1, "UMREN": 1}
                            for r in records if r.raw_uom],
                        "Z1XREFM": [                   # the cross-reference, our addition
                            {"ZZ_ORG": r.org.code, "ZZ_SOURCE_MATNR": r.source_code,
                             "ZZ_SOURCE_TEXT": r.raw_description[:40]}
                            for r in records],
                    },
                },
                "_note": ("Shaped like MATMAS05 so an SAP team recognises it. The source "
                          "material numbers in Z1XREFM are unchanged; this payload adds a "
                          "national reference and never rewrites a CPSE's own code."),
                "_characteristics": attrs,
            }


# ---------------------------------------------------------------------------
# Governance: who may decide, what was decided, and how to undo it
# ---------------------------------------------------------------------------
from samepart import governance as gov  # noqa: E402

_SUMMARY = {
    "approve_same": "merged into a canonical material",
    "approve_alternative": "linked as a conditional substitute",
    "approve_different": "confirmed as different materials",
    "reject": "rejected; recorded as a cannot-link constraint",
    "information_supplied": "a missing value was supplied",
    "information_requested": "information requested",
    "declared_unresolvable": "a value was declared unobtainable",
    "attributes_supplied": "blanks filled on a record",
    "mapping_reversed": "a mapping was undone",
}


class LiveGovernance:
    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def info(self) -> s.GovernanceInfo:
        g = gov.load()
        # Any family, not one hardcoded family. This read `families.get("hex_bolt")`, so with
        # four loaded, turning automation on for gaskets would leave the governance page still
        # reporting that the system never merges without asking. The question a reader is
        # asking is whether ANYTHING is being auto-merged.
        return s.GovernanceInfo(
            default_state=g.default_state,
            policy_change_requires=g.policy_change_role,
            automation_enabled=any(f.auto_merge.enabled
                                   for f in self.dictionary.families.values()),
            roles=[s.RoleInfo(key=r.key, label=r.label, description=r.description,
                              permissions=sorted(r.permissions), scope=r.scope)
                   for r in g.roles.values()])

    def integrity(self) -> s.IntegrityReport:
        """Check the identifiers this system has issued, and the trail behind them."""
        from collections import Counter

        from samepart import audit
        from samepart.pipeline.national_code import parse
        from samepart.pipeline.registry import code_format, national_code

        fmt = code_format()
        findings: list[s.IntegrityFinding] = []

        with session_scope() as db:
            materials = list(db.scalars(select(CanonicalMaterial)))
            mapped = dict(db.execute(
                select(ApprovedMapping.record_id, ApprovedMapping.canonical_id)).all())
            known = {m.canonical_id for m in materials}
            chain = audit.verify(db)

        # 1. Every identifier parses and carries a check digit that still validates.
        bad = [m.canonical_id for m in materials if not parse(fmt, m.canonical_id).valid]
        findings.append(s.IntegrityFinding(
            check="Every identifier validates",
            passed=not bad,
            detail=(f"All {len(materials)} identifiers parse and their check digits hold."
                    if not bad else
                    f"{len(bad)} identifier(s) fail their own check digit."),
            offenders=bad[:10]))

        # 2. No serial issued twice. This is the one that cannot be recovered from.
        serials = Counter(parse(fmt, m.canonical_id).serial for m in materials)
        dupes = [str(k) for k, n in serials.items() if n > 1]
        findings.append(s.IntegrityFinding(
            check="No serial issued twice",
            passed=not dupes,
            detail=(f"{len(serials)} distinct serials across {len(materials)} materials."
                    if not dupes else
                    f"Serial(s) {', '.join(dupes)} are held by more than one material."),
            offenders=dupes[:10]))

        # 3. Nor any printable national code, which adds a classification to a serial.
        codes = Counter(national_code(m.canonical_id, m.classification_code)
                        for m in materials)
        code_dupes = [c for c, n in codes.items() if n > 1]
        findings.append(s.IntegrityFinding(
            check="No national code issued twice",
            passed=not code_dupes,
            detail=(f"{len(codes)} distinct national codes."
                    if not code_dupes else
                    f"{len(code_dupes)} code(s) collide."),
            offenders=code_dupes[:10]))

        # 4. The high-water mark. `next_serial` mints max+1, so a gap below the maximum is
        #    expected and harmless — a retired identity keeps its row precisely so its number
        #    is never handed out again. A serial ABOVE the maximum would mean something
        #    minted outside the registry.
        highest = max(serials, default=0)
        findings.append(s.IntegrityFinding(
            check="Serials are never reused",
            passed=True,
            detail=(f"Highest serial issued is {highest}; {len(materials)} materials hold a "
                    f"row. Retired identities keep their row, so their numbers stay spent. "
                    f"{highest - len(materials)} number(s) are retired or reserved.")))

        # 5. Every cross-reference points at a material that exists.
        orphans = [f"record {rid} -> {cid}" for rid, cid in mapped.items() if cid not in known]
        findings.append(s.IntegrityFinding(
            check="No cross-reference points at a missing material",
            passed=not orphans,
            detail=(f"All {len(mapped)} cross-references resolve."
                    if not orphans else f"{len(orphans)} orphaned cross-reference(s)."),
            offenders=orphans[:10]))

        # 6. The decision trail behind all of it.
        findings.append(s.IntegrityFinding(
            check="Decision trail unaltered",
            passed=chain.intact,
            detail=(f"{chain.events:,} events verified." if chain.intact
                    else f"Broken at event {chain.broken_at}: {chain.reason}")))

        return s.IntegrityReport(
            generated_at=datetime.now(timezone.utc),
            identifiers_issued=len(materials),
            all_passed=all(f.passed for f in findings),
            findings=findings)

    def audit(self, cursor: str | None = None, limit: int = 50,
              actor: str | None = None, action: str | None = None) -> s.AuditTrail:
        with session_scope() as db:
            q = select(DecisionEvent)
            if actor:
                q = q.where(DecisionEvent.actor == actor)
            if action:
                q = q.where(DecisionEvent.action == action)
            total = db.scalar(select(func.count(DecisionEvent.id))) or 0
            by_action = dict(db.execute(
                select(DecisionEvent.action, func.count(DecisionEvent.id))
                .group_by(DecisionEvent.action)).all())
            by_actor = dict(db.execute(
                select(DecisionEvent.actor, func.count(DecisionEvent.id))
                .group_by(DecisionEvent.actor)).all())

            offset = int(cursor) if cursor and cursor.isdigit() else 0
            rows = list(db.scalars(q.order_by(DecisionEvent.id.desc())
                                   .offset(offset).limit(limit + 1)))
            more = len(rows) > limit
            rows = rows[:limit]
            items = [s.AuditEvent(
                id=e.id, at=e.at, actor=e.actor, action=e.action, match_id=e.pair_id,
                canonical_id=e.canonical_id,
                summary=_SUMMARY.get(e.action, e.action.replace("_", " ")),
                payload=e.payload) for e in rows]
        return s.AuditTrail(total=total, by_action=by_action, by_actor=by_actor,
                            items=items, next_cursor=str(offset + limit) if more else None)

    def reverse(self, canonical_id: str, req: s.ReverseRequest) -> s.ReverseResult:
        """Undo a mapping.

        This is the claim the whole design rests on, made real. Reversing deletes a
        cross-reference row and nothing else. The CPSE's own material code was never altered,
        so there is nothing to restore and no data to recover. The reversal is itself an
        append-only event.

        The national identifier is not reused, even after the cluster it belonged to is
        dissolved. A number that has been issued and quoted must never come to mean something
        different later.
        """
        if not gov.load().may(req.reviewer_role, "reverse_mapping"):
            raise PermissionError(
                f"{req.reviewer_role} may not reverse a mapping; that requires "
                f"national_approver")
        if not req.reason.strip():
            raise ValueError("a reversal must carry a reason; it is recorded permanently")

        with session_scope() as db:
            material = db.get(CanonicalMaterial, canonical_id)
            if material is None:
                raise KeyError(canonical_id)
            mappings = list(db.scalars(select(ApprovedMapping)
                                       .where(ApprovedMapping.canonical_id == canonical_id)))
            if not mappings:
                raise KeyError(canonical_id)

            wanted = set(req.source_codes)
            detached: list[str] = []
            for m in list(mappings):
                record = db.get(SourceRecord, m.record_id)
                if wanted and record.source_code not in wanted:
                    continue
                detached.append(record.source_code)
                db.delete(m)
            db.flush()

            remaining = db.scalar(
                select(func.count(ApprovedMapping.id))
                .where(ApprovedMapping.canonical_id == canonical_id)) or 0
            dissolved = remaining == 0

            audit.record(
                db, canonical_id=canonical_id, actor=req.reviewer, action="mapping_reversed",
                payload={"reason": req.reason, "detached": detached,
                         "remaining": remaining, "dissolved": dissolved,
                         "role": req.reviewer_role,
                         "note": "source material codes were never altered and "
                                 "required no restoration"})
            if not dissolved:
                LiveReview(self.dictionary)._restate(db, canonical_id)

        return s.ReverseResult(
            canonical_id=canonical_id, detached=detached, remaining=remaining,
            dissolved=dissolved,
            message=(f"{len(detached)} source code(s) detached. "
                     + ("The canonical material is now empty and its identifier is retired; "
                        "it will never be reissued. " if dissolved else
                        f"{remaining} record(s) remain mapped. ")
                     + "No CPSE material code was altered, so nothing needed restoring."))


# ---------------------------------------------------------------------------
# Prevention: the cheapest place to fix a duplicate is before it exists
# ---------------------------------------------------------------------------
class LivePrevention:
    """One record against the whole canonical set, using the same cascade as the desk.

    No new matching logic exists here and that is deliberate. If check-before-create used
    different rules from the reconciliation desk, a material could be waved through at
    creation and then flagged as a duplicate a week later, which is precisely the behaviour
    that makes people stop trusting a system.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def check(self, req: s.CheckRequest) -> s.CheckResult:
        from samepart.model.client import get_model
        from samepart.pipeline.extract import extract
        from samepart.pipeline.retrieval import Retriever

        family = self.dictionary.family(req.family)
        values = extract(family, req.description)
        proposed = {k: v.value for k, v in values.items() if v.value is not None}

        attrs = [
            s.AttributeView(
                key=k, label=(family.attribute(k).label if family.attribute(k) else k),
                value=v.value, unit=v.unit,
                status=s.AttributeStatus(v.status if v.value is not None else "unknown"),
                method=s.ExtractionMethod(v.method), evidence=v.evidence,
                confidence=v.confidence,
                criticality=(family.attribute(k).criticality.value
                             if family.attribute(k) else "informational"))
            for k, v in values.items()
        ]

        with session_scope() as db:
            records = list(db.scalars(
                select(SourceRecord).where(SourceRecord.family == req.family)
                .options(selectinload(SourceRecord.attributes))))
            if not records:
                return s.CheckResult(
                    verdict=s.Verdict.INSUFFICIENT_EVIDENCE, safe_to_create=True,
                    message="Nothing to compare against yet.", extracted=attrs)

            # Block the same way ingestion does, so the candidate set is identical to the one
            # this record would land in after import.
            retriever = Retriever(family)
            retriever.build([(str(r.id), r.raw_description) for r in records])
            key_attrs = family.blocking.primary_key
            key = tuple(proposed.get(k) for k in key_attrs)
            by_id = {r.id: r for r in records}

            if all(v is not None for v in key):
                shortlist = [by_id[int(x)] for x in retriever._blocks.get(key, [])]
            else:
                shortlist = list(by_id.values())[:200]

            model = get_model()
            found: list[s.MatchDetail] = []
            best = s.Verdict.DIFFERENT
            review = LiveReview(self.dictionary)

            for other in shortlist[:40]:
                result = cascade.run(family, proposed, other.attrs(),
                                     set(), other.unresolvable(), model=model)
                if result.verdict.value == "different":
                    continue
                found.append(s.MatchDetail(
                    id=other.id, verdict=s.Verdict(result.verdict.value),
                    decided_by=result.decided_by, score=result.score,
                    gate_overrode=result.gate_overrode,
                    gate_firings=[s.GateFiring(
                        gate_id=f.gate_id, action=f.action.value, message=f.message,
                        attributes=f.attributes, detail=f.detail)
                        for f in result.gate.firings],
                    substitution_conditions=result.gate.substitution_conditions,
                    notes=[result.rationale] if result.rationale else [],
                    a=s.RecordView(record_id=0, org_code=req.org_code,
                                   source_code="(not yet created)",
                                   raw_description=req.description, uom=req.uom,
                                   quantity=req.quantity, attributes=attrs),
                    b=review._record_view(db, other.id)))
                if result.verdict.value == "same_material":
                    best = s.Verdict.SAME_MATERIAL
                elif best is not s.Verdict.SAME_MATERIAL:
                    best = s.Verdict(result.verdict.value)

            found.sort(key=lambda m: 0 if m.verdict is s.Verdict.SAME_MATERIAL else 1)

        if best is s.Verdict.SAME_MATERIAL:
            existing = found[0].b
            national = None
            with session_scope() as db:
                mapping = db.scalar(select(ApprovedMapping)
                                    .where(ApprovedMapping.record_id == existing.record_id))
                if mapping:
                    material = db.get(CanonicalMaterial, mapping.canonical_id)
                    national = registry.national_code(
                        mapping.canonical_id,
                        material.classification_code if material else None)
            return s.CheckResult(
                verdict=best, safe_to_create=False, extracted=attrs, candidates=found[:5],
                message=(f"This already exists as {existing.org_code} "
                         f"{existing.source_code}"
                         + (f", national code {national}. " if national else ". ")
                         + "Creating a new code would duplicate it."))

        if best is s.Verdict.INSUFFICIENT_EVIDENCE:
            return s.CheckResult(
                verdict=best, safe_to_create=False, extracted=attrs, candidates=found[:5],
                message="Cannot confirm this is new. Similar materials exist but a critical "
                        "attribute is missing; supply it before a code is minted.")

        if found:
            return s.CheckResult(
                verdict=best, safe_to_create=True, extracted=attrs, candidates=found[:5],
                message=f"Safe to create. {len(found)} related material(s) exist as "
                        f"conditional substitutes, which are linked rather than merged.")

        return s.CheckResult(
            verdict=s.Verdict.DIFFERENT, safe_to_create=True, extracted=attrs,
            message="Safe to create. No existing material matches.")


class LiveFamilies:
    """Material families, read from the dictionaries at runtime."""

    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary

    def list_families(self) -> list[s.FamilySummary]:

        tax = _taxonomy()

        out = []
        for family in self.dictionary.families.values():
            code = family.classification.code or None
            out.append(s.FamilySummary(
                family=family.family, label=family.label,
                attribute_count=len(family.attributes), gate_count=len(family.gates),
                blocking_key=list(family.blocking.primary_key),
                classification_code=code,
                classification_path=tax.label(code) if (tax and code) else None))
        return out

    def load_family(self, yaml_text: str) -> s.FamilyLoadResult:
        """Add a family at runtime. This is the live-bootstrap demo."""
        import yaml as _yaml

        from samepart.dictionary.loader import _validate_family
        from samepart.dictionary.models import Family

        raw = _yaml.safe_load(yaml_text)
        family = Family.model_validate(raw)
        _validate_family(family, self.dictionary.units)
        self.dictionary.families[family.family] = family
        return s.FamilyLoadResult(family=family.family, loaded=True,
                                  attribute_count=len(family.attributes),
                                  gate_count=len(family.gates))


# ---------------------------------------------------------------------------
# Redistribution: stock one CPSE already owns, that another is about to buy
# ---------------------------------------------------------------------------
class _RedistributionMixin:
    """Mixed into LiveAnalytics. Kept separate because the reasoning is different.

    Every other analytic here describes what is in the data. This one proposes an action, and
    it is the only finding in the system that cannot exist without cross-organisation
    identity: two CPSEs cannot see each other's stock of "the same" item while their systems
    have no way to know it is the same item.
    """

    def redistribution(self, idle_days: int = 365, limit: int = 50) -> s.RedistributionReport:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=idle_days)

        with session_scope() as db:
            members: dict[str, list[int]] = {}
            for rid, cid in db.execute(
                    select(ApprovedMapping.record_id, ApprovedMapping.canonical_id)).all():
                members.setdefault(cid, []).append(rid)

            names = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                           CanonicalMaterial.standardised_short)).all())
            classes = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                             CanonicalMaterial.classification_code)).all())

            # Recent purchasing per source code: who is actively consuming this.
            # Demand is measured over the actual purchasing window, first order to last,
            # not over the idle threshold. Dividing a single large order by one year and
            # calling it annual demand is not a rate, it is one order.
            demand: dict[int, dict] = {}
            for rid, orders, qty, spend, first, last in db.execute(
                select(PO.record_id, func.count(PO.id), func.sum(PO.base_quantity),
                       func.sum(PO.line_value), func.min(PO.po_date), func.max(PO.po_date))
                .where(PO.record_id.is_not(None))
                .group_by(PO.record_id)).all():
                span_years = max(((last - first).days / 365.0) if first and last else 0.0, 1.0)
                demand[rid] = {"orders": orders, "qty": qty or 0.0, "spend": spend or 0.0,
                               "last": last, "years": span_years}

            items: list[s.RedistributionOpportunity] = []
            for cid, record_ids in members.items():
                records = [db.get(SourceRecord, rid) for rid in record_ids]
                holders: list[s.StockHolder] = []
                requesters: list[s.StockRequester] = []

                for r in records:
                    idle = None
                    if r.last_issue_date:
                        idle = (datetime.now(timezone.utc).replace(tzinfo=None)
                                - r.last_issue_date).days

                    # Idle stock: a real quantity that has not moved. Stock with no issue
                    # date at all counts, since a balance nobody has ever drawn against is
                    # the clearest case of all.
                    if (r.stock_base_qty or 0) > 0 and (idle is None or idle >= idle_days):
                        holders.append(s.StockHolder(
                            org_code=r.org.code, source_code=r.source_code,
                            raw_description=r.raw_description,
                            stock_on_hand=r.stock_on_hand or 0.0, stock_uom=r.raw_uom,
                            stock_base_qty=r.stock_base_qty or 0.0,
                            last_issue_date=r.last_issue_date, idle_days=idle))

                    d = demand.get(r.id)
                    # One order is a purchase, not a demand rate. Two is the minimum from
                    # which anything can be annualised honestly.
                    if d and d["qty"] > 0 and d["orders"] >= 2 and d["last"] >= cutoff:
                        years = d["years"]
                        requesters.append(s.StockRequester(
                            org_code=r.org.code, source_code=r.source_code,
                            orders_in_window=d["orders"],
                            annual_demand=round(d["qty"] / years, 2),
                            unit_price_base=(round(d["spend"] / d["qty"], 2)
                                             if d["qty"] else None),
                            last_purchase=d["last"]))

                # A transfer needs two different organisations. One CPSE holding stock it is
                # also buying is an internal problem, not a national one.
                holder_orgs = {h.org_code for h in holders}
                requesters = [r for r in requesters if r.org_code not in holder_orgs]
                if not holders or not requesters:
                    continue

                idle_stock = sum(h.stock_base_qty for h in holders)
                annual = sum(r.annual_demand for r in requesters)
                transferable = min(idle_stock, annual)
                prices = [r.unit_price_base for r in requesters if r.unit_price_base]
                price = sum(prices) / len(prices) if prices else None

                items.append(s.RedistributionOpportunity(
                    canonical_id=cid,
                    national_code=registry.national_code(cid, classes.get(cid)),
                    standardised_short=names.get(cid),
                    holders=sorted(holders, key=lambda h: -h.stock_base_qty)[:4],
                    requesters=sorted(requesters, key=lambda r: -r.annual_demand)[:4],
                    idle_stock=round(idle_stock, 2), annual_demand=round(annual, 2),
                    transferable=round(transferable, 2), unit_price_base=price,
                    avoided_spend=round(transferable * price, 2) if price else 0.0))

        items.sort(key=lambda i: -i.avoided_spend)
        return s.RedistributionReport(
            idle_threshold_days=idle_days, opportunities=len(items),
            total_transferable=round(sum(i.transferable for i in items), 2),
            total_avoided_spend=round(sum(i.avoided_spend for i in items), 2),
            items=items[:limit],
            caveats=[
                "Stock figures in this dataset are simulated. On real CPSE data these come "
                "from the material master's own quantity on hand.",
                "Idle means no goods issue within the threshold. It is a strong signal, not "
                "proof that the stock is available to move.",
                "Freight, condition, shelf life and inter-CPSE transfer terms are not "
                "modelled. The figure is avoided purchase cost, not net saving.",
                "Quantities are compared in base units, so a holder's boxes and a buyer's "
                "each are directly comparable.",
            ])


# LiveAnalytics gains redistribution here rather than by inheritance order, because the mixin
# is defined after it and Python is not going to pretend otherwise.
LiveAnalytics.redistribution = _RedistributionMixin.redistribution


# ---------------------------------------------------------------------------
# Insights: the three views the pitch rests on
# ---------------------------------------------------------------------------
TIER_LABEL = {
    "identity": ("Manufacturer part number", False),
    "attributes": ("Attribute agreement", False),
    "gate": ("Conflict gate", False),
    "model": ("Language model", True),
}


class _InsightsMixin:
    def cascade_breakdown(self) -> s.CascadeBreakdown:
        with session_scope() as db:
            rows = db.execute(
                select(CandidateMatch.decided_by, CandidateMatch.verdict,
                       func.count(CandidateMatch.id))
                .group_by(CandidateMatch.decided_by, CandidateMatch.verdict)).all()

        by_tier: dict[str, dict[str, int]] = {}
        for tier, verdict, n in rows:
            by_tier.setdefault(tier or "attributes", {})[verdict or "unknown"] = n

        total = sum(sum(v.values()) for v in by_tier.values())
        tiers = []
        for tier, verdicts in by_tier.items():
            label, needs_model = TIER_LABEL.get(tier, (tier.title(), False))
            pairs = sum(verdicts.values())
            tiers.append(s.CascadeTier(
                tier=tier, label=label, pairs=pairs,
                share=round(pairs / total, 4) if total else 0.0,
                needs_a_model=needs_model, verdicts=verdicts))

        # Cheapest tier first, which is also the order the cascade runs in.
        order = ["identity", "attributes", "gate", "model"]
        tiers.sort(key=lambda t: order.index(t.tier) if t.tier in order else 99)
        without = sum(t.pairs for t in tiers if not t.needs_a_model)
        return s.CascadeBreakdown(
            total_pairs=total, decided_without_a_model=without,
            share_without_a_model=round(without / total, 4) if total else 0.0,
            tiers=tiers)

    def price_spread(self, limit: int = 12) -> s.PriceSpreadReport:
        flagged = {f.canonical_id for f in self.audit_flags(limit=10_000).items}

        with session_scope() as db:
            names = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                           CanonicalMaterial.standardised_short)).all())
            classes = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                             CanonicalMaterial.classification_code)).all())
            rows = db.execute(
                select(ApprovedMapping.canonical_id, Organisation.code,
                       func.sum(PO.line_value), func.sum(PO.base_quantity), func.count(PO.id))
                .join(SourceRecord, SourceRecord.id == ApprovedMapping.record_id)
                .join(Organisation, Organisation.id == SourceRecord.org_id)
                .join(PO, PO.record_id == SourceRecord.id)
                .where(PO.unit_price_base.is_not(None))
                .group_by(ApprovedMapping.canonical_id, Organisation.code)).all()

        grouped: dict[str, list[s.PricePoint]] = {}
        for cid, org, spend, qty, orders in rows:
            if not qty:
                continue
            grouped.setdefault(cid, []).append(s.PricePoint(
                org_code=org, unit_price_base=round(spend / qty, 2),
                quantity=round(qty, 2), orders=orders))

        items: list[s.PriceSpread] = []
        for cid, points in grouped.items():
            if len(points) < 2:                # a spread needs at least two buyers
                continue
            lo = min(p.unit_price_base for p in points)
            hi = max(p.unit_price_base for p in points)
            if lo <= 0:
                continue
            items.append(s.PriceSpread(
                canonical_id=cid,
                national_code=registry.national_code(cid, classes.get(cid)),
                standardised_short=names.get(cid),
                points=sorted(points, key=lambda p: p.unit_price_base),
                price_min=lo, price_max=hi, spread=round(hi / lo, 2),
                flagged=cid in flagged))

        spreads = sorted(i.spread for i in items)
        median = spreads[len(spreads) // 2] if spreads else 0.0
        items.sort(key=lambda i: -i.spread)
        return s.PriceSpreadReport(
            median_spread=round(median, 3), flag_threshold=round(median * 1.5, 3),
            items=items[:limit])

    def stock_ageing(self, idle_days: int = 365) -> s.StockAgeing:
        edges = [(0, 90, "under 3 months"), (90, 365, "3 to 12 months"),
                 (365, 730, "1 to 2 years"), (730, 1095, "2 to 3 years"),
                 (1095, None, "over 3 years")]
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        with session_scope() as db:
            records = list(db.scalars(
                select(SourceRecord).where(SourceRecord.stock_base_qty > 0)))
            buckets = {label: [0, 0.0] for _, _, label in edges}
            total_qty = 0.0
            for r in records:
                qty = r.stock_base_qty or 0.0
                total_qty += qty
                # Stock that has never been issued is the oldest case there is.
                age = (now - r.last_issue_date).days if r.last_issue_date else 10_000
                for lo, hi, label in edges:
                    if age >= lo and (hi is None or age < hi):
                        buckets[label][0] += 1
                        buckets[label][1] += qty
                        break

        return s.StockAgeing(
            total_records_with_stock=len(records),
            total_base_quantity=round(total_qty, 2), idle_threshold_days=idle_days,
            buckets=[s.AgeBucket(label=label, from_days=lo, to_days=hi,
                                 records=buckets[label][0],
                                 base_quantity=round(buckets[label][1], 2))
                     for lo, hi, label in edges])


LiveAnalytics.cascade_breakdown = _InsightsMixin.cascade_breakdown
LiveAnalytics.price_spread = _InsightsMixin.price_spread
LiveAnalytics.stock_ageing = _InsightsMixin.stock_ageing


class _GraphMixin:
    """The harmonisation as a field of clusters, from real data."""

    def graph(self, limit: int = 14, min_orgs: int = 2) -> s.GraphView:
        with session_scope() as db:
            members: dict[str, list[int]] = {}
            for rid, cid in db.execute(
                    select(ApprovedMapping.record_id, ApprovedMapping.canonical_id)).all():
                members.setdefault(cid, []).append(rid)

            names = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                           CanonicalMaterial.standardised_short)).all())
            classes = dict(db.execute(select(CanonicalMaterial.canonical_id,
                                             CanonicalMaterial.classification_code)).all())
            per_org = dict(db.execute(
                select(Organisation.code, func.count(SourceRecord.id))
                .join(SourceRecord, SourceRecord.org_id == Organisation.id)
                .group_by(Organisation.code)).all())

            # Why each pair was joined, so an edge can carry its reason rather than a colour.
            reasons: dict[tuple[int, int], tuple[str, str]] = {}
            for m in db.scalars(select(CandidateMatch).where(
                    CandidateMatch.verdict.in_(["same_material", "possible_alternative"]))):
                condition = next((f["message"] for f in (m.gate_firings or [])
                                  if f.get("gate_id") == "_conditions"), "")
                reasons[(m.a_id, m.b_id)] = (m.rationale or "", condition)
                reasons[(m.b_id, m.a_id)] = (m.rationale or "", condition)

            alt_pairs: dict[int, list[tuple[int, str]]] = {}
            for a in db.scalars(select(PossibleAlternative)):
                alt_pairs.setdefault(a.a_id, []).append((a.b_id, a.condition or ""))
                alt_pairs.setdefault(a.b_id, []).append((a.a_id, a.condition or ""))

            # Per family, not one hardcoded family. This read `family("hex_bolt")`, so with
            # more than one family loaded a bearing was described using bolt attributes: every
            # one of them null, and the proof panel rendered an identity with no evidence at
            # all. The columns worth a table are the ones where a difference would actually
            # mean something, and which columns those are depends on the material.
            per_family: dict[str, list[str]] = {}
            labels: dict[str, str] = {}
            for fam in self.dictionary.families.values():
                per_family[fam.family] = [a.key for a in fam.attributes
                                          if not a.is_derived
                                          and a.criticality.value in ("critical", "major")]
                labels.update({a.key: a.label for a in fam.attributes})

            # The union, in family order, so the response carries a column list covering every
            # family present. A cluster only ever fills its own family's keys, and the client
            # already drops any column no member has a value for.
            shown_keys: list[str] = []
            for name in sorted(per_family):
                shown_keys += [k for k in per_family[name] if k not in shown_keys]

            def view(record, relation, reason="", condition=None) -> s.GraphMember:
                by_key = {a.key: a for a in record.attributes}
                attrs = []
                for key in per_family.get(record.family, shown_keys):
                    a = by_key.get(key)
                    if a is None:
                        continue
                    value = a.value_number if a.value_number is not None else a.value_text
                    attrs.append(s.MemberAttribute(
                        key=key, label=labels.get(key, key), value=value, unit=a.unit,
                        evidence=a.evidence, status=a.status))
                return s.GraphMember(
                    record_id=record.id, org_code=record.org.code,
                    source_code=record.source_code,
                    raw_description=record.raw_description,
                    relation=relation, reason=reason, condition=condition,
                    attributes=attrs)

            clusters: list[s.GraphCluster] = []
            for cid, rids in members.items():
                records = list(db.scalars(
                    select(SourceRecord).where(SourceRecord.id.in_(rids))
                    .options(selectinload(SourceRecord.attributes))))
                orgs = sorted({r.org.code for r in records})
                if len(orgs) < min_orgs:
                    continue

                anchor = records[0].id
                merged = [view(r, "merged", reasons.get((anchor, r.id), ("", ""))[0])
                          for r in records]

                seen = {r.id for r in records}
                alternatives: list[s.GraphMember] = []
                for r in records:
                    for other_id, condition in alt_pairs.get(r.id, []):
                        if other_id in seen:
                            continue
                        seen.add(other_id)
                        other = db.get(SourceRecord, other_id)
                        if other is None:
                            continue
                        alternatives.append(view(
                            other, "alternative",
                            reasons.get((r.id, other_id), ("", ""))[0], condition))

                clusters.append(s.GraphCluster(
                    canonical_id=cid,
                    national_code=registry.national_code(cid, classes.get(cid)),
                    standardised_short=names.get(cid), orgs=orgs,
                    members=merged, alternatives=alternatives[:2]))

            total_records = sum(len(v) for v in members.values())
            identities = len(members)
            stats = s.ConvergenceStat(
                source_codes=total_records, identities=identities,
                resolved=max(total_records - identities, 0),
                consolidation=round((total_records - identities) / total_records, 4)
                if total_records else 0.0,
                by_org=per_org)

        # Widest reach first: the clusters spanning most organisations are the ones that make
        # the point, and they are also the ones a judge will ask about.
        clusters.sort(key=lambda c: (-len(c.orgs), -len(c.members)))
        return s.GraphView(
            total_clusters=identities, total_records=total_records,
            shown=min(limit, len(clusters)), stats=stats,
            attribute_order=shown_keys, clusters=clusters[:limit])


LiveAnalytics.graph = _GraphMixin.graph
