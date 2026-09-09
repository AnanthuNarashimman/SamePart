"""The API contract.

These models ARE the agreement between backend and frontend. FastAPI publishes them as
OpenAPI, and the frontend generates its TypeScript from that, so neither side hand-writes
the other's types. Changing a field here changes the frontend's types on its next
generation, which is why contract changes are a conversation rather than a commit.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    SAME_MATERIAL = "same_material"
    POSSIBLE_ALTERNATIVE = "possible_alternative"
    DIFFERENT = "different"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewState(str, Enum):
    QUEUED = "queued"
    APPROVED = "approved"
    REJECTED = "rejected"
    INFO_REQUESTED = "info_requested"


class AttributeStatus(str, Enum):
    EXTRACTED = "extracted"
    UNKNOWN = "unknown"
    DERIVED = "derived"


class ExtractionMethod(str, Enum):
    REGEX = "regex"
    LLM = "llm"
    DERIVED = "derived"
    GIVEN = "given"


class Org(BaseModel):
    code: str
    name: str
    simulated: bool = True
    record_count: int = 0


class AttributeView(BaseModel):
    """One extracted fact, with the words that justified it.

    The frontend renders `unknown` rows explicitly rather than hiding them. A missing
    critical attribute is the reason the system is asking a question, so it has to be seen.
    """
    key: str
    label: str
    value: str | float | None = None
    unit: str | None = None
    status: AttributeStatus = AttributeStatus.EXTRACTED
    method: ExtractionMethod = ExtractionMethod.REGEX
    evidence: str | None = Field(None, description="Substring of the source description that proved this value")
    confidence: float | None = None
    criticality: str = "informational"


class RecordView(BaseModel):
    record_id: int
    org_code: str
    source_code: str
    raw_description: str
    standardised_short: str | None = None
    uom: str | None = None
    base_uom: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    unit_price_base: float | None = None
    currency: str = "INR"
    attributes: list[AttributeView] = Field(default_factory=list)


class GateFiring(BaseModel):
    gate_id: str
    action: str
    message: str
    attributes: list[str] = Field(default_factory=list)
    detail: str = ""


class MatchDetail(BaseModel):
    id: int
    verdict: Verdict
    decided_by: str = Field(description="Which cascade tier decided: deterministic, classifier, or model")
    score: float | None = None
    review_state: ReviewState = ReviewState.QUEUED
    gate_overrode: bool = False
    gate_firings: list[GateFiring] = Field(default_factory=list)
    substitution_conditions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    a: RecordView
    b: RecordView


class QueueItem(BaseModel):
    id: int
    verdict: Verdict
    review_state: ReviewState
    a_description: str
    b_description: str
    a_org: str
    b_org: str
    headline: str = Field(description="One line saying why this pair is here")


class QueueCounts(BaseModel):
    needs_input: int = 0
    possible_alternative: int = 0
    same_material: int = 0
    different: int = 0


class QueuePage(BaseModel):
    counts: QueueCounts
    items: list[QueueItem]
    next_cursor: str | None = None


class DecisionAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_INFO = "request_info"


class DecisionRequest(BaseModel):
    action: DecisionAction
    note: str | None = None
    provided_attributes: dict[str, str] | None = Field(
        None, description="Answers to a request_info, keyed by attribute"
    )
    reviewer: str = "demo-reviewer"


class DecisionResult(BaseModel):
    match_id: int
    new_state: ReviewState
    canonical_id: str | None = None
    verdict: Verdict
    message: str


class ColumnSuggestion(BaseModel):
    field: str
    column: str | None = None
    confidence: float = Field(description="1.0 is an exact header match; below 0.9 is a guess")
    how: str
    alternatives: list[str] = Field(default_factory=list)


class ImportPreview(BaseModel):
    """What a file looks like before committing to importing it.

    The mapping is proposed, not imposed. Confident matches are pre-filled so nobody maps a
    familiar export by hand, and anything uncertain is surfaced with alternatives.
    """
    kind: str
    headers: list[str]
    sample_rows: list[dict] = Field(default_factory=list)
    suggestions: list[ColumnSuggestion] = Field(default_factory=list)
    column_map: dict[str, str] = Field(
        default_factory=dict, description="Send this straight back to POST /imports")
    ready: bool = Field(description="True when every required field found a column")
    missing_required: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    org_code: str
    family: str
    column_map: dict[str, str] = Field(default_factory=dict)


class ImportStatus(BaseModel):
    import_id: str
    org_code: str
    status: str
    rows_read: int = 0
    rows_ingested: int = 0
    rows_skipped: int = Field(0, description="Rows already present. Re-importing is safe.")
    attributes_extracted: int = 0
    errors: list[str] = Field(
        default_factory=list,
        description="Things that went WRONG. An import with an empty errors list succeeded.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Things worth knowing that are not failures, such as rows skipped "
                    "because they were already imported. Render these differently from "
                    "errors; a re-import that skips everything is correct behaviour, not "
                    "a failure.")
    started_at: datetime | None = None

    # Matching runs automatically after ingestion, scoped to the rows that arrived.
    candidate_pairs: int = Field(0, description="Pairs compared involving the new records")
    auto_merged: int = Field(0, description="Merged by rule with nobody asked")
    queued_for_review: int = Field(0, description="Pairs now waiting for a person")
    matched_at: datetime | None = None


class CheckRequest(BaseModel):
    description: str
    org_code: str
    family: str = "hex_bolt"
    uom: str | None = None
    quantity: float | None = None


class CheckResult(BaseModel):
    verdict: Verdict
    safe_to_create: bool
    message: str
    extracted: list[AttributeView] = Field(default_factory=list)
    candidates: list[MatchDetail] = Field(default_factory=list)


class OrgDuplicateStat(BaseModel):
    org_code: str
    records: int
    mapped_to_canonical: int
    duplicate_rate: float
    dead_codes: int


class AnalyticsSummary(BaseModel):
    records: int
    canonical_materials: int
    merged: int
    conflicts_caught: int
    duplicate_rate: float
    queue_by_group: QueueCounts

    # From procurement history
    procurement_lines: int = 0
    total_spend: float = 0.0
    spend_window: str | None = None
    dead_codes: int = Field(0, description="Material codes with no purchase order in the window")
    dead_code_rate: float = 0.0
    shared_materials: int = Field(0, description="Canonical materials bought by more than one CPSE")
    currency: str = "INR"
    by_org: list[OrgDuplicateStat] = Field(default_factory=list)


class DeadCode(BaseModel):
    record_id: int
    org_code: str
    source_code: str
    raw_description: str
    canonical_id: str | None = None
    last_purchase: str | None = None


class RationalisationResult(BaseModel):
    """Legacy material code rationalisation, capability 5.

    A code nobody has ordered in the window is a candidate for closure. This list cannot be
    produced from material master data alone; it needs purchase history.
    """
    window: str
    records: int
    dead_codes: int
    dead_code_rate: float
    duplicate_codes_removable: int = Field(
        0, description="Codes that are duplicates of another and could collapse into it")
    items: list[DeadCode] = Field(default_factory=list)


class AuditFlag(BaseModel):
    canonical_id: str
    standardised_short: str | None = None
    reason: str
    price_spread: float
    orgs: list[str] = Field(default_factory=list)
    source_codes: list[str] = Field(default_factory=list)


class AuditFlagResult(BaseModel):
    """Merges the system nominates for a second look.

    Procurement history plays no part in making a merge, so a cluster whose spending pattern
    is far outside the norm is flagged by evidence the matcher never saw. Measured on the
    generated data, correctly merged clusters differ about 1.40x on unit price while
    incorrectly merged ones differ about 2.34x.
    """
    median_spread_all: float
    threshold: float
    flagged: int
    items: list[AuditFlag] = Field(default_factory=list)


class SavingsCluster(BaseModel):
    canonical_id: str
    standardised_short: str
    orgs: list[str]
    price_min: float
    price_max: float
    spread_pct: float
    total_quantity: float
    total_spend: float = 0.0
    po_lines: int = 0
    aggregation_opportunity: float = Field(description="Spend above the lowest observed unit price")


class SavingsResult(BaseModel):
    """Aggregation opportunity, with the untrustworthy merges taken out.

    A cluster the audit check has flagged is a cluster we are not confident is one material.
    Counting its price spread as a saving would be quoting our own error as a benefit, so
    flagged clusters are excluded from the headline and reported separately.
    """
    currency: str = "INR"
    total_opportunity: float
    total_spend: float = 0.0
    shared_materials: int = 0
    window: str | None = None
    excluded_flagged_clusters: int = 0
    excluded_opportunity: float = Field(
        0.0, description="Opportunity NOT claimed, because those merges are under audit")
    clusters: list[SavingsCluster]


class CounterpartValue(BaseModel):
    """What other records in the blocked pairs say for this field, to help the reviewer."""
    value: str
    seen_on: int


class MissingField(BaseModel):
    key: str
    label: str
    criticality: str
    pairs_blocked: int
    counterpart_values: list[CounterpartValue] = Field(
        default_factory=list,
        description="Values the other side of the blocked pairs carries. Often the answer is "
                    "visible from context, which is why we show it rather than asking blind.",
    )


class Question(BaseModel):
    """One record with one or more blanks, and what filling them unblocks.

    The queue holds pairs, but a person does not answer pairs. The same record appears in
    many blocked pairs, and one answer clears all of them, so the reviewer is asked about
    records and ranked by how much each answer is worth.
    """
    record_id: int
    org_code: str
    source_code: str
    raw_description: str
    missing: list[MissingField]
    pairs_blocked: int = Field(description="Pairs this one record is blocking, across all its blanks")


class QuestionPage(BaseModel):
    pairs_deferred: int
    questions: int = Field(description="Distinct record-and-field blanks behind those pairs")
    records: int = Field(description="Records a person actually opens")
    curve: list[CurvePoint] = Field(
        default_factory=list,
        description="Diminishing returns. Answering in ranked order, how many pairs clear "
                    "after N answers. Shown so a data owner can stop early on purpose "
                    "rather than feeling obliged to empty the queue.",
    )
    items: list[Question]
    next_cursor: str | None = None


class AnswerRequest(BaseModel):
    values: dict[str, str] = Field(description="Attribute key -> value the reviewer asserts")
    reviewer: str = "demo-reviewer"
    note: str | None = None


class UnresolvableRequest(BaseModel):
    keys: list[str] = Field(description="Attributes that cannot be answered from any source")
    reason: str | None = None
    reviewer: str = "demo-reviewer"


class CurvePoint(BaseModel):
    questions_answered: int
    pairs_cleared: int
    share_cleared: float


class AnswerResult(BaseModel):
    record_id: int
    applied: dict[str, str]
    pairs_reevaluated: int
    resolved: QueueCounts = Field(description="What the unblocked pairs became")
    message: str


class FamilySummary(BaseModel):
    family: str
    label: str
    attribute_count: int
    gate_count: int
    blocking_key: list[str] = Field(default_factory=list)


class FamilyLoadResult(BaseModel):
    family: str
    loaded: bool
    attribute_count: int
    gate_count: int
