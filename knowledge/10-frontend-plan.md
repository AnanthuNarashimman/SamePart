# Frontend plan

What pages the UI needs, what each one does, and why — reconciled against the gaps and
priorities already recorded in this knowledge base. Where this plan disagrees with the
original project doc, the reason is cited.

## The two families

Every page belongs to one of two moments in a material's lifecycle, plus a third category
that only reports on them.

- **Migrate family** — reconciling data that already exists (bulk import from multiple
  CPSEs, one-time or periodic).
- **Create family** — stopping a *new* duplicate at the moment someone tries to create it
  (ongoing, one record at a time).
- **Report family** — read-only views over what the other two have already decided. Writes
  nothing, triggers no pipeline step.

## Pages

### 1. Import / Ingestion — *Migrate*
Upload CSV/Excel per source "company," a per-source column-mapping config (not a hardcoded
parser), and extraction status once regex/LLM extraction runs. Entry point before anything
else — nothing downstream exists until this has run.

### 2. Reconciliation Desk — *Migrate* (primary, build first)
The working screen. Three parts:

- **Queue**, grouped by verdict rather than a flat mixed list — this was the concrete change
  we made in this session. Four groups, ordered by reviewer priority, not alphabetically or
  by verdict-label order:
  1. **Needs input** (`insufficient_evidence`) — the system is explicitly stuck and asking a
     question; highest priority.
  2. **Possible alternatives** — a substitute relationship, not an identity merge; needs
     engineer judgment, not a rubber stamp.
  3. **Confirmed matches** (`same_material`) — mostly a quick-approve pass.
  4. **Confirmed different** — lowest priority, informational, collapsed by default.

  Do not conflate group 2 and group 4 into one "less similar" bucket — they are different
  *kinds* of outcome, not points on one similarity scale.
- **Comparison view** — side-by-side typed attributes with evidence and provenance per
  field, the proposed verdict, and which conflict gate fired (if any).
- **Actions** — approve / reject / request-information.

**Two additions this session's knowledge-base review surfaces that the original page
description was missing:**

- **Survivorship display on approve.** [09-open-decisions.md](09-open-decisions.md) #8 asks,
  unanswered: when records merge into one canonical material, whose description and whose
  specification wins? The comparison view needs a moment — at minimum, showing which
  source's value was kept per field on the merged canonical record — even if the underlying
  rule (newest wins, most-complete wins, manual pick) stays simple for the prototype. Silence
  here is a gap a judge will find, not a detail to skip.
- **Fields the comparison view should carry, once available:** manufacturer + manufacturer
  part number (highest-precision identity signal in real material masters — see
  [08-ranked-additions.md](08-ranked-additions.md) #3), unit of measurement (named twice in
  the problem statement, absent from the schema per
  [02-problem-statement-coverage.md](02-problem-statement-coverage.md)), and a standardized
  description shown next to the raw source description ([08] #4). None of these change the
  page's structure — they're additional attribute rows in the same comparison layout.

### 3. Duplicate-Prevention Check — *Create*
A single-record check reusing the same pipeline against the full canonical set instead of a
batch. Entry form → match-found (existing canonical record + evidence, same comparison
component as the Desk) or no-match/safe-to-create. No queue, no grouping — one session, one
verdict.

Per [08-ranked-additions.md](08-ranked-additions.md), this is arguably the highest-ROI
feature in the system but was fifth of six in the original demo script — worth promoting
earlier in both the build order and the demo, not just leaving last.

### 4. Dashboard & Analytics — *Report* (new; added this session)
The project plan explicitly cut this ("Explicitly cut for time," §2 of the original plan)
in favor of the matching pipeline. That trade was right for where the hard engineering risk
sits — but [02-problem-statement-coverage.md](02-problem-statement-coverage.md) scores
**"Material master dashboard & analytics" as capability #6 of 8, status Missing**, and notes
it is *"the only place the PS's nine impact bullets can be proven."* Cutting it entirely
leaves a named, checklist capability with zero coverage and no way to answer "how much money
does this save" — one of the fourteen judge questions in
[03-gaps-and-judge-questions.md](03-gaps-and-judge-questions.md) currently marked **No
answer**.

Scope stays deliberately small — this is not the "full ablation/benchmark dashboard" that
stays cut (that's ML-metric comparison between matching paths, a different thing entirely).
This is an operational summary, cheap because it's pure aggregation over tables the system
already writes (`approved_mapping`, `candidate_match`, `possible_alternative`,
`known_conflict`, canonical registry, event log):

- Counts: records imported, canonical materials created, duplicates merged, conflicts
  caught, queue size by group
- **Money view** — demand aggregation and price variance once price/quantity/unit exist on
  records ([08] Tier 1 #1, ~3h, "produces the only number a judge repeats later")
- Unit-of-measure harmonization status, once UOM is added to the schema

Promote this over the Relationship Graph as the page most worth building next, given it
closes a named capability gap the graph does not.

### 5. Relationship Graph — *Report* (demoted; keep only if time allows)
Static, curated node graph of one demo cluster — read-only, no new backend logic, built
last, first cut if short on time. This was the plan's original "closing visual." It stays in
scope only if hours remain: [08-ranked-additions.md](08-ranked-additions.md) lists it
explicitly under **Deprioritise** — *"pretty, says little a judge cares about."* The
Dashboard now serves as the stronger closing beat; the graph is optional polish underneath
it, not a replacement for it.

## Build priority (revised)

1. Reconciliation Desk — proves the pipeline end-to-end, now with grouped queue
2. Import — needed to get data in at all
3. Duplicate-prevention check — cheap, highest-ROI, promote earlier than the original
   fifth-of-six demo slot
4. Dashboard & Analytics — closes a named capability gap and the impact-quantification gap;
   cheap because it's aggregation over existing tables
5. Relationship Graph — only if time remains

## Still open, not resolved by this plan
Survivorship rules (design the actual rule, not just the display), and whether/how the
Dashboard should respect a multi-tenancy boundary between CPSEs
([09-open-decisions.md](09-open-decisions.md) #9) once more than one organization's data is
in view at once.
