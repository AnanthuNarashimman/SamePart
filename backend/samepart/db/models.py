"""Relational model.

Two principles are enforced here rather than by convention. Source codes are never
overwritten: a canonical identity is an additional row, and every mapping points back to
the CPSE record it came from. And decisions are append-only: nothing is updated in place,
so the audit trail is the table, not a report generated from one.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = "organisation"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    simulated: Mapped[bool] = mapped_column(default=True)

    records: Mapped[list["SourceRecord"]] = relationship(back_populates="org")


class SourceRecord(Base):
    """One line of one CPSE's material master, exactly as received."""
    __tablename__ = "source_record"
    __table_args__ = (
        UniqueConstraint("org_id", "source_code", name="uq_org_source_code"),
        Index("ix_source_record_family", "family"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"))
    source_code: Mapped[str] = mapped_column(String(64))
    raw_description: Mapped[str] = mapped_column(Text)
    family: Mapped[str] = mapped_column(String(64))

    raw_uom: Mapped[str | None] = mapped_column(String(32), default=None)
    base_uom: Mapped[str | None] = mapped_column(String(32), default=None)
    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    base_quantity: Mapped[float | None] = mapped_column(Float, default=None)
    unit_price: Mapped[float | None] = mapped_column(Float, default=None)
    unit_price_base: Mapped[float | None] = mapped_column(Float, default=None)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    # Stock on hand. A real material master carries this; ours did not, and inferring
    # "sitting unused" from a gap in purchase history is a much weaker claim than reading
    # the quantity. Modelled explicitly so the analysis reads a field rather than a proxy.
    stock_on_hand: Mapped[float | None] = mapped_column(Float, default=None)
    stock_base_qty: Mapped[float | None] = mapped_column(Float, default=None)
    last_issue_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    row_ref: Mapped[str | None] = mapped_column(String(64), default=None)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Ground truth, populated only for generated data. Never read by the pipeline.
    truth_identity: Mapped[str | None] = mapped_column(String(64), default=None)

    org: Mapped[Organisation] = relationship(back_populates="records")
    attributes: Mapped[list["ExtractedAttribute"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )

    def unresolvable(self) -> set[str]:
        """Blanks a person has declared unanswerable. Never asked about again."""
        return {a.key for a in self.attributes if a.status == "unresolvable"}

    def attrs(self) -> dict[str, object]:
        """Attribute view the matcher and gates consume."""
        out: dict[str, object] = {}
        for a in self.attributes:
            if a.status in ("unknown", "unresolvable"):
                continue
            out[a.key] = a.value_number if a.value_number is not None else a.value_text
        return out


class ExtractedAttribute(Base):
    """A typed attribute with the evidence that produced it.

    Evidence is per field, not per record, because a reviewer needs to know which words in
    which description justified this particular value.
    """
    __tablename__ = "extracted_attribute"
    __table_args__ = (UniqueConstraint("record_id", "key", name="uq_record_attr"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    key: Mapped[str] = mapped_column(String(64))

    value_text: Mapped[str | None] = mapped_column(String(200), default=None)
    value_number: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str | None] = mapped_column(String(32), default=None)

    # extracted | unknown | derived | unresolvable
    # `unresolvable` means a person looked and the answer does not exist anywhere. It stops
    # the pair being asked about again, forever, instead of sitting in a queue.
    status: Mapped[str] = mapped_column(String(16), default="extracted")
    method: Mapped[str] = mapped_column(String(16), default="regex")      # regex|llm|derived|given
    evidence: Mapped[str | None] = mapped_column(String(300), default=None)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)

    record: Mapped[SourceRecord] = relationship(back_populates="attributes")


class ProcurementLine(Base):
    """One purchase order line, as recorded by one CPSE.

    The problem statement names historical procurement data as an INPUT to the analysis, not
    only as a source of savings figures. It earns its place three times over:

    - **Analytics.** Real spend and real price variance across CPSEs, rather than one price
      column on a master record
    - **Rationalisation.** A material code with no purchase order in three years is a dead
      code. That list is legacy rationalisation, and it cannot be produced without this
    - **Matching evidence.** The same vendor and vendor part number appearing in two CPSEs'
      order history is strong identity evidence, independent of how either wrote the
      description

    Quantities and prices are normalised to base units at ingestion, exactly as master
    records are, because one box of a hundred and a hundred each must be comparable before
    any aggregation is valid.
    """
    __tablename__ = "procurement_line"
    __table_args__ = (
        UniqueConstraint("org_id", "po_number", "line_no", name="uq_po_line"),
        Index("ix_po_source_code", "org_id", "source_code"),
        Index("ix_po_date", "po_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisation.id"))
    record_id: Mapped[int | None] = mapped_column(ForeignKey("source_record.id"), default=None)
    source_code: Mapped[str] = mapped_column(String(64))

    po_number: Mapped[str] = mapped_column(String(64))
    line_no: Mapped[int] = mapped_column(Integer, default=1)
    po_date: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vendor: Mapped[str | None] = mapped_column(String(160), default=None)
    vendor_part_number: Mapped[str | None] = mapped_column(String(64), default=None)
    plant: Mapped[str | None] = mapped_column(String(32), default=None)

    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    uom: Mapped[str | None] = mapped_column(String(32), default=None)
    base_quantity: Mapped[float | None] = mapped_column(Float, default=None)
    base_uom: Mapped[str | None] = mapped_column(String(32), default=None)
    unit_price: Mapped[float | None] = mapped_column(Float, default=None)
    unit_price_base: Mapped[float | None] = mapped_column(Float, default=None)
    line_value: Mapped[float | None] = mapped_column(Float, default=None)
    currency: Mapped[str] = mapped_column(String(8), default="INR")


class CandidateMatch(Base):
    """A pair the retrieval tier surfaced, plus whatever the cascade decided about it."""
    __tablename__ = "candidate_match"
    __table_args__ = (
        UniqueConstraint("a_id", "b_id", name="uq_candidate_match"),
        Index("ix_candidate_match_verdict", "verdict"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    b_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))

    retrieval_score: Mapped[float | None] = mapped_column(Float, default=None)
    decided_by: Mapped[str | None] = mapped_column(String(24), default=None)  # which cascade tier
    score: Mapped[float | None] = mapped_column(Float, default=None)
    verdict: Mapped[str | None] = mapped_column(String(32), default=None)
    rationale: Mapped[str | None] = mapped_column(Text, default=None)
    gate_firings: Mapped[list | None] = mapped_column(JSON, default=None)
    gate_overrode: Mapped[bool] = mapped_column(default=False)
    review_state: Mapped[str] = mapped_column(String(16), default="queued")  # queued|approved|rejected|info
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DecisionEvent(Base):
    """Append-only. Never updated, never deleted."""
    __tablename__ = "decision_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    pair_id: Mapped[int | None] = mapped_column(ForeignKey("candidate_match.id"), default=None)
    canonical_id: Mapped[str | None] = mapped_column(String(32), default=None)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(32), default="")
    payload: Mapped[dict | None] = mapped_column(JSON, default=None)
    at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CanonicalMaterial(Base):
    __tablename__ = "canonical_material"

    canonical_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    family: Mapped[str] = mapped_column(String(64))
    standardised_short: Mapped[str | None] = mapped_column(String(200), default=None)
    standardised_long: Mapped[str | None] = mapped_column(Text, default=None)
    classification_code: Mapped[str | None] = mapped_column(String(32), default=None)
    attributes: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ApprovedMapping(Base):
    """The cross-reference. A CPSE keeps its own code; this row records what it means."""
    __tablename__ = "approved_mapping"
    __table_args__ = (UniqueConstraint("record_id", name="uq_approved_mapping_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_id: Mapped[str] = mapped_column(ForeignKey("canonical_material.canonical_id"))
    record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    approved_by: Mapped[str] = mapped_column(String(64), default="system")
    at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class KnownConflict(Base):
    """A cannot-link constraint. Survives clustering; nothing may merge across it."""
    __tablename__ = "known_conflict"
    __table_args__ = (UniqueConstraint("a_id", "b_id", name="uq_conflict"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    b_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="gate")  # gate|reviewer


class PossibleAlternative(Base):
    """A substitution relation. Separate identities, conditionally interchangeable."""
    __tablename__ = "possible_alternative"
    __table_args__ = (UniqueConstraint("a_id", "b_id", name="uq_alternative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    b_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    condition: Mapped[str] = mapped_column(Text, default="")
