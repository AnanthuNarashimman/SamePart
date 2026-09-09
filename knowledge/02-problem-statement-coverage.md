# Coverage against the problem statement

SIH26099 lists eight key capabilities. Evaluators treat that list as a checklist, because
it is one. Here is where the plan stands against it.

## The eight named capabilities

| # | Capability as written in the PS | Status | Where we stand |
|---|---|---|---|
| 1 | AI material matching & recommendation | **Strong** | Our core bet. Four-way verdict over typed, evidenced attributes. |
| 2 | Material standardization & classification | **Partial** | Attributes are extracted but no standardized description is ever emitted, and there is no taxonomy classifier at all. |
| 3 | Duplicate / near-duplicate detection | **Strong** | Covered, including functional equivalents as a separate verdict. |
| 4 | Common national material code generation | **Weak** | `SMP-000417` is a bare counter. No structure, no anchor, no owning body. |
| 5 | CPSE code mapping & migration support | **Partial** | Mapping yes. Bulk legacy rationalisation and a loadable migration output, barely. |
| 6 | Material master dashboard & analytics | **Missing** | Explicitly cut. This is the only place the PS's nine impact bullets can be proven. |
| 7 | Audit trail & governance | **Partial** | Event log yes. Governance, meaning who approves a national code across organisations, absent. |
| 8 | SAP / ERP integration | **Missing** | Explicitly cut in favour of local processes. |

**Score: 2 strong, 4 partial or weak, 2 missing.**

## The second, quieter checklist

The PS background paragraph names five axes on which the same material diverges across
CPSEs:

> "different material codes, **descriptions**, **specifications**, **units of measurement**
> and **classification**"

- Codes — handled
- Descriptions — handled
- Specifications — handled
- **Units of measurement — absent from our schema entirely**
- **Classification — not handled**

Unit of measure is not a detail. The same bolt held as each, as a box of a hundred, and by
weight is precisely why cross-CPSE demand cannot be aggregated today. It is named twice in
the problem statement.

## Expected Impact: nine bullets, all economic

The PS impact section is almost entirely about money: duplicate reduction, inventory
optimisation, procurement cost reduction through demand aggregation, faster procurement,
data-driven decisions, a foundation for strategic sourcing.

**Our plan quantifies none of it.** Impact is a fifth of the deck score.

## What the plan gets right, and must survive editing

Do not let the criticism above erase these. They are why this plan is better than the
median entry.

- Evidence and provenance carried **per extracted field**, not per record
- A four-way verdict that permits refusal instead of forcing a binary
- Conflict gates held **outside** the model, auditable, able to veto it
- Canonical IDs minted by a registry, **never invented by a language model**
- Source codes never overwritten; mapping is strictly additive
- Duplicate prevention at the moment of creation
- Cluster safety against contradicting an already-accepted attribute
- Honest labelling of synthetic data, and honest lists of what was cut
