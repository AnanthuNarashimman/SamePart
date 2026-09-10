# The plan, re-anchored to the problem statement

Written after noticing we had spent a long session deepening capabilities 1 and 3, which
were already our strongest, while 2, 4, 5, 6, 7 and 8 stayed where they were.

**Rule from here: work is chosen by what the problem statement names and we do not have,
not by what is interesting.**

## Coverage as of 10 September 2026: all eight capabilities covered

Every capability the problem statement names now has an implementation. What follows is the
assessment that started this plan, kept for the record.

## Honest coverage, when this plan was written

| # | Capability | Status | What is actually missing |
|---|---|---|---|
| 1 | AI matching & recommendation | Strong mechanically | **No AI in it.** Regex and deterministic rules only |
| 2 | Standardization & classification | Half | Descriptions are generated on merge but never surfaced. **Classification absent** |
| 3 | Duplicate / near-duplicate detection | Strong | Measured and defensible |
| 4 | Common national material code | Weak | A bare counter with no structure or owner |
| 5 | CPSE mapping & migration support | Half | Mapping works. **Migration and rationalisation absent** |
| 6 | Dashboard & analytics | Missing | Nothing at all |
| 7 | Audit trail & governance | Half | Audit trail is real and append-only. **Governance absent** |
| 8 | SAP / ERP integration | Missing | Nothing at all |

## Two things in the PS text we had been skipping

**"Artificial Intelligence, Machine Learning and Natural Language Processing (NLP)"** are
named explicitly. We run none of the three. Everything working today is regular expressions
and a rule table. That is good engineering and a bad answer to "show me the AI." Both the
classification model and the model tier exist to close this.

**"...and historical procurement data from multiple CPSEs."** Named as an *input* to the
analysis, not merely as a source of savings figures. It is not in our data model at all.
This is now the next thing we build, because it unlocks three capabilities rather than one:

- **Capability 6, analytics.** Real spend, real price variance, real demand aggregation
  across CPSEs, instead of a single price column on a master record
- **Capability 5, rationalisation.** A material code with no purchase order in three years is
  a dead code. That list *is* legacy rationalisation, and it cannot be produced without
  procurement history
- **Capability 1, matching evidence.** The same vendor and the same vendor part number
  appearing in two CPSEs' order history is strong identity evidence, independent of how
  either wrote the description

## On "user validation and approval workflow"

The PS says the system should provide matching and recommendation capabilities "**allowing**
users to review, validate and approve proposed mappings."

*Allowing.* The requirement is that the workflow exists and is available, not that a person
must approve every mapping individually. Automation is therefore not disallowed. The posture
we will build to:

- **Default: everything is reviewable.** Auto-merge is off until a CPSE turns it on
- **Anything a model decided is always reviewed.** Deterministic rule outcomes may be
  automated; inference may not. This holds automatically once the model tier lands
- **The policy itself is what a person approves**, once, attributably, instead of clicking
  approve hundreds of times
- **Every automated decision stays reversible.** Mapping is additive, so un-merging is a row
  delete

## Order of work

| # | Work | Capability | Why here |
|---|---|---|---|
| A ✅ | **Procurement history as a first-class input** | 1, 5, 6 | Unlocks three capabilities. Everything below leans on it |
| B ✅ | **Dashboard and analytics** | 6 | Wholly absent, cheapest on the list, delivers six of the nine impact bullets |
| C ✅ | **Classification into a taxonomy** | 2 | The missing half, and the honest trained-ML artifact |
| D ✅ | **Common national material code** | 4 | Mostly a structure and governance decision |
| E ✅ | **Model tier for extraction and matching** | 1, 2 | Puts the NLP in, and cuts the 207 open blanks by reading whole records |
| F ✅ | **ERP integration and legacy migration** | 5, 8 | Both named, both currently zero |
| G ✅ | **Governance** | 7 | Roles, two-tier approval, who owns the automation policy |

Stopped deliberately: further tuning of the human queue. 288 actions is defensible and past
the point of returns.

## What procurement history looks like in the data model

A separate line-level table, ingested per CPSE alongside the material master:

`org, source_code, po_number, po_date, vendor, vendor_part_number, quantity, uom, unit_price, currency, plant`

Quantities and prices are normalised to base units at ingestion, exactly as the master
records already are, because a purchase of one box of a hundred and a purchase of a hundred
each must be comparable before any aggregation is valid.
