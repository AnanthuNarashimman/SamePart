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
    reviewer_role: str = Field(
        "national_approver",
        description="viewer | steward | national_approver | administrator")
    reviewer_org: str | None = Field(
        None, description="Required for a steward, whose authority is their own CPSE only")


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
    family: str = Field(
        description="Which material family to read this description as. Required, and "
                    "deliberately not defaulted: checking a gasket against a bolt's patterns "
                    "extracts nothing, finds no duplicate, and cheerfully says the code is "
                    "safe to create.")
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
    national_code: str | None = Field(
        None, description="Printable Common National Material Code, classification included")
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
    reviewer_role: str = Field(
        "national_approver", description="viewer | steward | national_approver | administrator")
    reviewer_org: str | None = Field(
        None, description="A steward's own CPSE; they may answer only for its records")
    note: str | None = None


class UnresolvableRequest(BaseModel):
    keys: list[str] = Field(description="Attributes that cannot be answered from any source")
    reason: str | None = None
    reviewer: str = "demo-reviewer"
    reviewer_role: str = Field(
        "national_approver", description="viewer | steward | national_approver | administrator")
    reviewer_org: str | None = Field(
        None, description="A steward's own CPSE; they may answer only for its records")


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


class CrossReferenceRow(BaseModel):
    """One line of the deliverable a CPSE actually loads into its own system.

    The CPSE's own code is the first column and is never altered. Everything after it is
    additional information about that code, which is the entire political proposition: you
    keep your master, you gain a national reference.
    """
    org_code: str
    source_code: str
    national_code: str | None = None
    canonical_identity: str | None = None
    classification_code: str | None = None
    classification_path: str | None = None
    standardised_short: str | None = None
    base_uom: str | None = None
    status: str = Field(description="active | duplicate | dead | unmapped")
    duplicate_of: str | None = Field(
        None, description="The source code this one duplicates, where it does")
    approved_by: str | None = None
    approved_at: datetime | None = None


class CrossReferenceExport(BaseModel):
    generated_at: datetime
    rows: int
    mapped: int
    dead: int
    duplicates: int
    items: list[CrossReferenceRow] = Field(default_factory=list)


class MigrationPlan(BaseModel):
    """Legacy material code rationalisation, as a plan a stores team can act on."""
    generated_at: datetime
    total_codes: int
    keep: int = Field(description="Codes that stay, one per canonical material")
    collapse: int = Field(description="Codes that duplicate another and can be cross-referenced")
    close: int = Field(description="Codes with no purchase order in the window")
    review: int = Field(description="Codes the system would not decide alone")
    estimated_codes_removed: int
    notes: list[str] = Field(default_factory=list)


class PassportSource(BaseModel):
    """One CPSE's code, exactly as it was received. Never altered by anything here."""
    org_code: str
    source_code: str
    raw_description: str
    base_uom: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None


class PassportEvidence(BaseModel):
    """One attribute, the value agreed for it, and who independently said so."""
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    stated_by: list[str] = Field(default_factory=list)
    differs: dict[str, str] = Field(
        default_factory=dict,
        description="Organisations that stated something else, and what they stated")
    evidence: dict[str, str] = Field(
        default_factory=dict,
        description="Source code -> the exact words the value was read from")


class PassportSubstitute(BaseModel):
    org_code: str
    source_code: str
    raw_description: str
    condition: str | None = None


class PassportDecision(BaseModel):
    at: datetime
    actor: str
    action: str
    note: str | None = None
    entry_hash: str | None = None


class MaterialPassport(BaseModel):
    """Everything known about one national identity, in one record a person can hand over.

    The proof panel already renders all of this; the passport is the same content as a
    portable artefact. A CPSE asked to accept a national code is entitled to the full basis
    for it -- which codes it covers, which organisation independently stated each fact, the
    words each fact was read from, who approved the merge and when, and whether that record
    has been altered since. Handing over a number and asking for trust is what these
    programmes usually do, and it is why they stall.
    """
    canonical_id: str
    national_code: str | None = None
    family: str
    classification_code: str | None = None
    standardised_short: str | None = None
    standardised_long: str | None = None
    issued_at: datetime

    sources: list[PassportSource] = Field(default_factory=list)
    evidence: list[PassportEvidence] = Field(default_factory=list)
    substitutes: list[PassportSubstitute] = Field(default_factory=list)
    decisions: list[PassportDecision] = Field(default_factory=list)

    audit_chain_intact: bool = Field(
        description="Whether the decision trail verified at the moment this was issued. A "
                    "passport carrying decisions from a broken chain says so.")
    audit_note: str = ""


class MigrationChange(BaseModel):
    org_code: str
    source_code: str
    action: str = Field(description="cross_reference | review | close_recommended")
    national_code: str | None = None
    reason: str = ""


class MigrationPreview(BaseModel):
    """What loading this into a CPSE's master would actually do, before anyone does it.

    The number that matters is `fields_altered`, and it is zero by construction rather than by
    policy: the export writes new columns beside a CPSE's own code and issues no update to any
    field the CPSE already owns. That claim is the reason a plant team will run this at all, so
    it is stated as a count they can check rather than a promise in a slide.
    """
    org_code: str | None = None
    generated_at: datetime
    codes_in_master: int
    rows_added: int
    fields_altered: int = 0
    columns_written: list[str] = Field(default_factory=list)
    columns_read_only: list[str] = Field(default_factory=list)
    by_action: dict[str, int] = Field(default_factory=dict)
    sample: list[MigrationChange] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class IntegrityFinding(BaseModel):
    check: str
    passed: bool
    detail: str
    offenders: list[str] = Field(default_factory=list)


class IntegrityReport(BaseModel):
    """Whether the identifiers this system has issued are sound.

    Not a reassurance panel. Every check here is a property that could genuinely fail, stated
    so that a failure is visible rather than absorbed: a check digit that no longer validates,
    two materials issued the same serial, a cross-reference pointing at a material that no
    longer exists, or a decision trail that has been edited.

    The serial check matters most and is the least obvious. Identifiers are minted as
    `max(existing) + 1`, so the guarantee that a serial is never reused depends entirely on
    retired materials being kept rather than deleted. If a dissolved identity were ever removed
    from the table, its number would be handed to the next material and two different things
    would share a national code across time — the one failure this scheme cannot recover from,
    because the CPSEs holding the old cross-reference would never know.
    """
    generated_at: datetime
    identifiers_issued: int
    all_passed: bool
    findings: list[IntegrityFinding] = Field(default_factory=list)


class AuditEvent(BaseModel):
    id: int
    at: datetime
    actor: str
    action: str
    match_id: int | None = None
    canonical_id: str | None = None
    summary: str = ""
    payload: dict | None = None


class AuditTrail(BaseModel):
    """Append-only. Nothing in here is updated or deleted, including reversals."""
    total: int
    by_action: dict[str, int] = Field(default_factory=dict)
    by_actor: dict[str, int] = Field(default_factory=dict)
    items: list[AuditEvent] = Field(default_factory=list)
    next_cursor: str | None = None


class ReverseRequest(BaseModel):
    reason: str = Field(description="Why this mapping is being undone. Recorded permanently.")
    reviewer: str = "demo-reviewer"
    reviewer_role: str = "national_approver"
    source_codes: list[str] = Field(
        default_factory=list,
        description="Detach only these records. Empty means dissolve the whole cluster.")


class ReverseResult(BaseModel):
    canonical_id: str
    detached: list[str] = Field(default_factory=list)
    remaining: int
    dissolved: bool
    message: str


class RoleInfo(BaseModel):
    key: str
    label: str
    description: str
    permissions: list[str]
    scope: str = "all"


class GovernanceInfo(BaseModel):
    default_state: str
    policy_change_requires: str
    automation_enabled: bool
    roles: list[RoleInfo] = Field(default_factory=list)


class StockHolder(BaseModel):
    org_code: str
    source_code: str
    raw_description: str
    stock_on_hand: float
    stock_uom: str | None = None
    stock_base_qty: float
    last_issue_date: datetime | None = None
    idle_days: int | None = None


class StockRequester(BaseModel):
    org_code: str
    source_code: str
    orders_in_window: int
    annual_demand: float = Field(description="Base units bought per year, recent average")
    unit_price_base: float | None = None
    last_purchase: datetime | None = None


class RedistributionOpportunity(BaseModel):
    """One CPSE is sitting on stock another is about to buy.

    This is the only finding in the system that is impossible without cross-organisation
    identity. Neither party can see it today, because the two describe the same item
    differently and their systems have no way to know it is the same thing.
    """
    canonical_id: str
    national_code: str | None = None
    standardised_short: str | None = None
    holders: list[StockHolder] = Field(default_factory=list)
    requesters: list[StockRequester] = Field(default_factory=list)
    idle_stock: float = Field(description="Base units sitting unissued")
    annual_demand: float = Field(description="Base units the requesters buy per year")
    transferable: float = Field(description="What could move: the lesser of the two")
    unit_price_base: float | None = None
    avoided_spend: float = Field(description="Cost of buying what could be transferred")


class RedistributionResult:
    pass


class RedistributionReport(BaseModel):
    currency: str = "INR"
    idle_threshold_days: int
    opportunities: int
    total_transferable: float
    total_avoided_spend: float
    caveats: list[str] = Field(default_factory=list)
    items: list[RedistributionOpportunity] = Field(default_factory=list)


class CascadeTier(BaseModel):
    tier: str
    label: str
    pairs: int
    share: float
    needs_a_model: bool
    verdicts: dict[str, int] = Field(default_factory=dict)


class CascadeBreakdown(BaseModel):
    """Which tier settled each pair.

    The point of the picture: the overwhelming majority never reach a model. That answers
    "where is the AI" and "does this scale" at once, and it is the strongest technical claim
    in the system.
    """
    total_pairs: int
    decided_without_a_model: int
    share_without_a_model: float
    tiers: list[CascadeTier] = Field(default_factory=list)


class PricePoint(BaseModel):
    org_code: str
    unit_price_base: float
    quantity: float
    orders: int


class PriceSpread(BaseModel):
    canonical_id: str
    national_code: str | None = None
    standardised_short: str | None = None
    points: list[PricePoint] = Field(default_factory=list)
    price_min: float
    price_max: float
    spread: float = Field(description="Highest divided by lowest")
    flagged: bool = Field(description="Spread far enough above the norm to suspect the merge")


class PriceSpreadReport(BaseModel):
    currency: str = "INR"
    median_spread: float
    flag_threshold: float
    items: list[PriceSpread] = Field(default_factory=list)


class AgeBucket(BaseModel):
    label: str
    from_days: int
    to_days: int | None = None
    records: int
    base_quantity: float


class StockAgeing(BaseModel):
    """How long redistribution candidates have been sitting."""
    total_records_with_stock: int
    total_base_quantity: float
    idle_threshold_days: int
    buckets: list[AgeBucket] = Field(default_factory=list)


class MemberAttribute(BaseModel):
    """One extracted fact and the exact words that proved it.

    `evidence` is the substring of the raw description the value came from. It is what turns
    "the words barely match, the attributes do" from a claim into something a reader can
    check by eye.
    """
    key: str
    label: str
    value: str | float | None = None
    unit: str | None = None
    evidence: str | None = None
    status: str = "extracted"


class GraphMember(BaseModel):
    record_id: int
    org_code: str
    source_code: str
    raw_description: str
    relation: str = Field(description="merged | alternative")
    reason: str = ""
    condition: str | None = None
    attributes: list[MemberAttribute] = Field(default_factory=list)


class GraphCluster(BaseModel):
    canonical_id: str
    national_code: str | None = None
    standardised_short: str | None = None
    standardised_long: str | None = Field(
        None, description="The labelled standard description: noun, then every attribute named")
    orgs: list[str] = Field(default_factory=list)
    members: list[GraphMember] = Field(default_factory=list)
    alternatives: list[GraphMember] = Field(default_factory=list)


class ConvergenceStat(BaseModel):
    source_codes: int
    identities: int
    resolved: int = Field(description="Codes that collapsed into an existing identity")
    consolidation: float = Field(description="Share of codes that were redundant")
    by_org: dict[str, int] = Field(default_factory=dict)


class GraphView(BaseModel):
    """Many clusters at once, not one.

    A single cluster in isolation looks like a diagram of something obvious. A field of them
    is the harmonisation itself: dozens of separate identities, each pulling records in from
    organisations that had no way of knowing they were describing the same thing.
    """
    total_clusters: int
    total_records: int
    shown: int
    stats: ConvergenceStat | None = None
    attribute_order: list[str] = Field(
        default_factory=list,
        description="Attribute keys worth showing in the evidence table, in dictionary order")
    clusters: list[GraphCluster] = Field(default_factory=list)


class FamilySummary(BaseModel):
    family: str
    label: str
    attribute_count: int
    gate_count: int
    blocking_key: list[str] = Field(default_factory=list)
    classification_code: str | None = None
    classification_path: str | None = None
    added: bool = Field(False, description="Loaded at runtime rather than shipped in the repository")


class FamilyRemoveResult(BaseModel):
    family: str
    removed: bool
    records_removed: int = 0


class FamilyLoadResult(BaseModel):
    family: str
    label: str = ""
    loaded: bool
    replaced: bool = False
    attribute_count: int
    gate_count: int
