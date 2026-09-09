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
    attributes_extracted: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None


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


class AnalyticsSummary(BaseModel):
    records: int
    canonical_materials: int
    merged: int
    conflicts_caught: int
    duplicate_rate: float
    queue_by_group: QueueCounts


class SavingsCluster(BaseModel):
    canonical_id: str
    standardised_short: str
    orgs: list[str]
    price_min: float
    price_max: float
    spread_pct: float
    total_quantity: float
    aggregation_opportunity: float = Field(description="Spend above the lowest observed unit price")


class SavingsResult(BaseModel):
    currency: str = "INR"
    total_opportunity: float
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
