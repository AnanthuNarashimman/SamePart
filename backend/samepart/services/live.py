"""Live service implementations, backed by the database and the pipeline.

Each class satisfies one protocol in `protocols.py` and is selected in `api/deps.py`. They
are added one at a time; anything not yet implemented stays on its stub, and the frontend
cannot tell the difference.
"""
from __future__ import annotations

import uuid
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
