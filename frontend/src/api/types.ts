// Hand-mirrors backend/samepart/api/schemas.py, which is the actual contract (FastAPI
// publishes it as OpenAPI). Field names and shapes must match exactly — this is not
// mock data, it is the type layer over the real API.

export type Verdict = 'same_material' | 'possible_alternative' | 'different' | 'insufficient_evidence'

// The live matcher can also write "auto_approved" directly to the DB (see
// backend/samepart/services/live.py) even though it is not in the schemas.py ReviewState
// enum yet. Typed as an open union so the UI does not break if the API returns it.
export type ReviewState = 'queued' | 'approved' | 'rejected' | 'info_requested' | 'auto_approved'

export type AttributeStatus = 'extracted' | 'unknown' | 'derived'
export type ExtractionMethod = 'regex' | 'llm' | 'derived' | 'given'
export type DecisionAction = 'approve' | 'reject' | 'request_info'

export interface Org {
  code: string
  name: string
  simulated: boolean
  record_count: number
}

export interface AttributeView {
  key: string
  label: string
  value: string | number | null
  unit: string | null
  status: AttributeStatus
  method: ExtractionMethod
  evidence: string | null
  confidence: number | null
  criticality: string
}

export interface RecordView {
  record_id: number
  org_code: string
  source_code: string
  raw_description: string
  standardised_short: string | null
  uom: string | null
  base_uom: string | null
  quantity: number | null
  unit_price: number | null
  unit_price_base: number | null
  currency: string
  attributes: AttributeView[]
}

export interface GateFiring {
  gate_id: string
  action: string
  message: string
  attributes: string[]
  detail: string
}

export interface MatchDetail {
  id: number
  verdict: Verdict
  decided_by: string
  score: number | null
  review_state: ReviewState
  gate_overrode: boolean
  gate_firings: GateFiring[]
  substitution_conditions: string[]
  notes: string[]
  a: RecordView
  b: RecordView
}

export interface QueueItem {
  id: number
  verdict: Verdict
  review_state: ReviewState
  a_description: string
  b_description: string
  a_org: string
  b_org: string
  headline: string
}

export interface QueueCounts {
  needs_input: number
  possible_alternative: number
  same_material: number
  different: number
}

export interface QueuePage {
  counts: QueueCounts
  items: QueueItem[]
  next_cursor: string | null
}

export interface DecisionRequest {
  action: DecisionAction
  note?: string | null
  provided_attributes?: Record<string, string> | null
  reviewer?: string
}

export interface DecisionResult {
  match_id: number
  new_state: ReviewState
  canonical_id: string | null
  verdict: Verdict
  message: string
}

export interface ImportRequest {
  org_code: string
  family: string
  column_map: Record<string, string>
}

export interface ImportStatus {
  import_id: string
  org_code: string
  status: string
  rows_read: number
  rows_ingested: number
  attributes_extracted: number
  errors: string[]
  started_at: string | null
}

export interface CheckRequest {
  description: string
  org_code: string
  family?: string
  uom?: string | null
  quantity?: number | null
}

export interface CheckResult {
  verdict: Verdict
  safe_to_create: boolean
  message: string
  extracted: AttributeView[]
  candidates: MatchDetail[]
}

export interface OrgDuplicateStat {
  org_code: string
  records: number
  mapped_to_canonical: number
  duplicate_rate: number
  dead_codes: number
}

export interface AnalyticsSummary {
  records: number
  canonical_materials: number
  merged: number
  conflicts_caught: number
  duplicate_rate: number
  queue_by_group: QueueCounts
  procurement_lines: number
  total_spend: number
  spend_window: string | null
  dead_codes: number
  dead_code_rate: number
  shared_materials: number
  currency: string
  by_org: OrgDuplicateStat[]
}

export interface DeadCode {
  record_id: number
  org_code: string
  source_code: string
  raw_description: string
  canonical_id: string | null
  last_purchase: string | null
}

export interface RationalisationResult {
  window: string
  records: number
  dead_codes: number
  dead_code_rate: number
  duplicate_codes_removable: number
  items: DeadCode[]
}

export interface AuditFlag {
  canonical_id: string
  standardised_short: string | null
  reason: string
  price_spread: number
  orgs: string[]
  source_codes: string[]
}

export interface AuditFlagResult {
  median_spread_all: number
  threshold: number
  flagged: number
  items: AuditFlag[]
}

export interface SavingsCluster {
  canonical_id: string
  standardised_short: string
  orgs: string[]
  price_min: number
  price_max: number
  spread_pct: number
  total_quantity: number
  total_spend: number
  po_lines: number
  aggregation_opportunity: number
}

export interface SavingsResult {
  currency: string
  total_opportunity: number
  total_spend: number
  shared_materials: number
  window: string | null
  excluded_flagged_clusters: number
  excluded_opportunity: number
  clusters: SavingsCluster[]
}

export interface CounterpartValue {
  value: string
  seen_on: number
}

export interface MissingField {
  key: string
  label: string
  criticality: string
  pairs_blocked: number
  counterpart_values: CounterpartValue[]
}

export interface Question {
  record_id: number
  org_code: string
  source_code: string
  raw_description: string
  missing: MissingField[]
  pairs_blocked: number
}

export interface CurvePoint {
  questions_answered: number
  pairs_cleared: number
  share_cleared: number
}

export interface QuestionPage {
  pairs_deferred: number
  questions: number
  records: number
  curve: CurvePoint[]
  items: Question[]
  next_cursor: string | null
}

export interface AnswerRequest {
  values: Record<string, string>
  reviewer?: string
  note?: string | null
}

export interface UnresolvableRequest {
  keys: string[]
  reason?: string | null
  reviewer?: string
}

export interface AnswerResult {
  record_id: number
  applied: Record<string, string>
  pairs_reevaluated: number
  resolved: QueueCounts
  message: string
}

export interface FamilySummary {
  family: string
  label: string
  attribute_count: number
  gate_count: number
  blocking_key: string[]
}
