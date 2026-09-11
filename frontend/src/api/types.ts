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
  reviewer_role?: string
  reviewer_org?: string | null
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

export interface MemberAttribute {
  key: string
  label: string
  value: string | number | null
  unit: string | null
  evidence: string | null
  status: string
}

export interface ConvergenceStat {
  source_codes: number
  identities: number
  resolved: number
  consolidation: number
  by_org: Record<string, number>
}

export interface GraphMember {
  record_id: number
  org_code: string
  source_code: string
  raw_description: string
  relation: 'merged' | 'alternative'
  reason: string
  condition: string | null
  attributes: MemberAttribute[]
}

export interface GraphCluster {
  canonical_id: string
  national_code: string | null
  standardised_short: string | null
  orgs: string[]
  members: GraphMember[]
  alternatives: GraphMember[]
}

export interface GraphView {
  total_clusters: number
  total_records: number
  shown: number
  stats: ConvergenceStat | null
  attribute_order: string[]
  clusters: GraphCluster[]
}

export interface CascadeTier {
  tier: string
  label: string
  pairs: number
  share: number
  needs_a_model: boolean
  verdicts: Record<string, number>
}

export interface CascadeBreakdown {
  total_pairs: number
  decided_without_a_model: number
  share_without_a_model: number
  tiers: CascadeTier[]
}

export interface PricePoint {
  org_code: string
  unit_price_base: number
  quantity: number
  orders: number
}

export interface PriceSpread {
  canonical_id: string
  national_code: string | null
  standardised_short: string | null
  points: PricePoint[]
  price_min: number
  price_max: number
  spread: number
  flagged: boolean
}

export interface PriceSpreadReport {
  currency: string
  median_spread: number
  flag_threshold: number
  items: PriceSpread[]
}

export interface AgeBucket {
  label: string
  from_days: number
  to_days: number | null
  records: number
  base_quantity: number
}

export interface StockAgeing {
  total_records_with_stock: number
  total_base_quantity: number
  idle_threshold_days: number
  buckets: AgeBucket[]
}

export interface StockHolder {
  org_code: string
  source_code: string
  raw_description: string
  stock_on_hand: number
  stock_uom: string | null
  stock_base_qty: number
  last_issue_date: string | null
  idle_days: number | null
}

export interface StockRequester {
  org_code: string
  source_code: string
  orders_in_window: number
  annual_demand: number
  unit_price_base: number | null
  last_purchase: string | null
}

export interface RedistributionOpportunity {
  canonical_id: string
  national_code: string | null
  standardised_short: string | null
  holders: StockHolder[]
  requesters: StockRequester[]
  idle_stock: number
  annual_demand: number
  transferable: number
  unit_price_base: number | null
  avoided_spend: number
}

export interface RedistributionReport {
  currency: string
  idle_threshold_days: number
  opportunities: number
  total_transferable: number
  total_avoided_spend: number
  caveats: string[]
  items: RedistributionOpportunity[]
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
  reviewer_role?: string
  reviewer_org?: string | null
  note?: string | null
}

export interface UnresolvableRequest {
  keys: string[]
  reason?: string | null
  reviewer?: string
  reviewer_role?: string
  reviewer_org?: string | null
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
