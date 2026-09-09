# What to build next, ranked by return per hour

## Tier 1 — do these before anything currently listed as a stretch goal

| # | Addition | Cost | Why |
|---|---|---|---|
| 1 | **Money view: demand aggregation + price variance** | ~3 h | Add price, quantity, unit to records. Once clusters exist this is a grouping query. Produces the only number a judge repeats later. Answers 6 of the PS's 9 impact bullets |
| 2 | **Unit of measure harmonization** | ~2 h | Named twice in the PS, absent from our schema, and required before any price comparison is valid |
| 3 | **Manufacturer + manufacturer part number** | ~2 h | Highest-precision identity signal in real material masters. Gives a deterministic rule needing no model call, and makes records look real to a domain judge |
| 4 | **Standardized description generation** | ~2 h | A named capability with zero coverage. Template fill in noun-modifier order once typed attributes exist. Show source vs standardized, side by side |
| 5 | **Taxonomy classifier** | ~4 h | A required capability *and* a genuine trained artifact. Better answer to "where is your ML" than the pairwise classifier, because it also ticks a box. Consider doing this **instead of** the pairwise Path B |

## Tier 2 — answers the killer questions, mostly slideware plus small code

| # | Addition | Cost | Why |
|---|---|---|---|
| 6 | **State the scale cascade with numbers** | ~1 h | Deterministic → blocking → cheap classifier → model on the ambiguous band only. State what fraction reaches the model and the cost for 2M records |
| 7 | **Calibration + auto-merge threshold** | ~2 h | Reverses our "no calibrated scores" decision. Report % auto-decided vs % queued. Turns an assistant into something that scales |
| 8 | **On-premises / sovereignty story** | slide + config flag | Open-weight model in the CPSE VPC, hosted API for prototype only. Must exist before we are asked |
| 9 | **ERP-shaped export** | ~2 h | Cross-reference table plus an IDoc- or OData-shaped payload. No real SAP needed. Converts a cut capability into a ticked one |
| 10 | **Governance model** | ~1 h | Who mints and owns the national code, two-tier approval, dispute path. Slide, not code |
| 11 | **Reviewer decisions fed back as labels** | ~3 h | Every approve and reject is a labelled pair; published work reaches usable models on tens of them. Makes the system visibly improve during the demo |

## Tier 3 — the wow moment

**12. Live new-family bootstrap.** Instead of hardcoding a second material family, add one
live: paste an attribute dictionary and gate rows for gaskets or bearings, and the system
starts matching that family with no code change.

This turns our single-family weakness into proof of generalisation. It requires that schema
and gates are **data, not code** — an architectural decision that is cheap on day one and
expensive later.

## Deprioritise

- Relationship graph view — pretty, says little a judge cares about
- A second hardcoded material family — replaced by #12
- Ablation dashboard
- The pairwise Path B classifier, **if** #5 is built instead

## Keep exactly as is

- Evidence and provenance per field
- Four-way verdict with `insufficient_evidence`
- Deterministic conflict gates outside the model
- Additive canonical ID; source codes never overwritten
- Registry-minted IDs, never model-invented
- Duplicate prevention at creation — but **promote it** in the demo order. It is currently
  fifth of six and it is arguably the highest-ROI feature in the whole system
