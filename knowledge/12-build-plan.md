# Build plan

Ordered steps to take the backend from stubs to live. Each step has an exit condition you
can check, and each one flips one service in `api/deps.py` from stub to live without the
frontend changing.

**Rule:** finish a step before starting the next. Each produces the data the next one reads.

---

## Step 1 — Live ingestion ✅ DONE
**Flips:** `catalogue_service` · shipped 2026-09-09

- CSV loader with per-source column mapping, not a hardcoded parser
- Persist `Organisation` and `SourceRecord`, normalising unit of measure, quantity and price
  to base units at ingestion so prices are comparable later
- Run regex extraction, persist every `ExtractedAttribute` with its evidence span and status
- Leave attributes regex cannot fill as `unknown`. Do not guess

**Exit:** posting a real CSV to `/api/imports` populates the database, and `/api/orgs`
returns real record counts.

## Step 2 — Live matching and review queue
**Flips:** `review_service` · the biggest step, and the demo spine

- Build the retriever over ingested records, generate candidate pairs
- Cascade tier 1: deterministic identity on manufacturer plus normalised part number
- Cascade tier 2: attribute agreement over typed values
- Run the conflict gates on every verdict; persist `CandidateMatch` with gate firings
- Queue, match detail and decision endpoints read real rows
- Approve mints a canonical id from the registry, writes `ApprovedMapping` and a
  `DecisionEvent`; reject writes a `KnownConflict` cannot-link constraint

**Exit:** the full demo runs end to end on real data **with no model call at all**. Blocking
plus deterministic gates already resolve the clean merge, the grade conflict, the missing
attribute and the substitution case. An API outage cannot break the demo.

## Step 3 — Standardised descriptions and survivorship
Closes [09-open-decisions.md](09-open-decisions.md) #8.

- Generate the short and long description from the **merged attribute set**, in noun-modifier
  order, using the family's template
- Survivorship rule: **do not pick a winning record**. Synthesise the canonical description
  from the union of evidenced attributes, and surface conflicting values rather than
  silently dropping one

**Exit:** approving a match shows a generated standardised description beside both sources.

## Step 4 — The model tier
**Uses:** Azure chat deployment `gpt-5.6-terra`, already verified

- Chat client behind one interface so a local open-weight model is a config swap
- Model-backed extraction **only** for attributes regex left unknown, with a strict schema
  that permits `unknown` as an answer
- Model pairwise verdict **only** for pairs the deterministic tiers could not settle
- Log which tier decided every pair

**Exit:** measured and reported — what share of pairs reach the model, and accuracy against
the labels.

## Step 5 — Evaluation harness
This is what turns a demo into evidence. See [06](06-entity-resolution-literature.md).

- Pairwise precision, recall and F1, plus B-cubed cluster metrics
- Coverage against risk: the share auto-decided at a held precision, and the auto-merge
  threshold that follows
- Blocking pairs completeness and reduction ratio (already measured: 100% and 98.4% clean,
  88.1% under extraction failure)

**Exit:** one numbers table, ready for the deck, with synthetic clearly labelled as a
designed ceiling.

## Step 6 — Analytics
**Flips:** `analytics_service` · cheap, because it is aggregation over tables already written

- Summary counts, duplicate rate, queue by group
- Price variance and demand aggregation across identity clusters, using **base-unit** prices

**Exit:** a rupee figure computed from real clusters, not a fixture.

## Step 7 — Prevention live
**Flips:** `check_service`

`/api/check` runs the same cascade for one new record against the canonical set. No new
matching logic.

**Exit:** entering a new description surfaces the existing canonical material before a code
is minted.

## Step 8 — Evaluate on real data
See [07-datasets.md](07-datasets.md). Detail in the section below.

**Exit:** a second accuracy number from real records, reported **separately** from the
synthetic one, never blended.

## Step 9 — Live family bootstrap
**Flips:** `family_service`

`POST /api/families` validates and loads a family YAML at runtime. Everything already reads
families as data, so this is validation and a registry reload.

**Exit:** a judge names a category, we paste a dictionary, the system starts matching it.

## Step 10 — Demo hardening
Offline path with no network call in the critical flow, seeded demo cases verified after
every change, and a rehearsed script.

---

## The real dataset: US defence logistics catalogue

The only public dataset found with genuine "one item, many codes" ground truth.

| File | Contents | Rows |
|---|---|---|
| `REFERENCE.zip` → `V_FLIS_PART.CSV` | `NIIN, PART_NUMBER, CAGE_CODE, RNCC, RNVC` | 16,442,614 |
| `IDENTIFICATION.zip` → `P_FLIS_NSN.CSV` | Item name and nomenclature per stock number | 16.9M |
| `IDENTIFICATION.zip` → `V_FLIS_STANDARDIZATION.CSV` | **Explicit item-to-item equivalence** | 378,572 |
| `CAGE.zip` → `P_CAGE.CSV` | Manufacturer code → real company name | 4M |

Roughly 7.2M unique item identification numbers, some carrying over a thousand
cross-referenced part numbers from different manufacturers.

**Why it fits us exactly.** One permanent item number is the canonical identity, and many
manufacturer part numbers map onto it. That is the structure our system claims to
reconstruct, with the answer already known. The standardization table is a **second,
independent** signal: explicit item-to-item equivalence, which maps onto our
`possible_alternative` verdict rather than `same_material`.

**How to use it without drowning.** Filter to the fastener federal supply classes — 5305
screws, 5306 bolts, 5307 studs, 5310 nuts and washers — which matches the family we already
model. A few thousand item numbers is plenty. Join in manufacturer names and item
nomenclature.

**Caveats, state them out loud.**
- US military catalogue data, not Indian public sector procurement
- The many codes are **manufacturer part numbers**, not four organisations' internal codes.
  Structurally the same problem, not the same context
- `dla.mil` returns 403 to automated fetchers. A human with a browser should succeed;
  archived mirrors from 2025 worked
- The item-characteristics file was not confirmed reachable, so typed attributes may have to
  come from parsing the item name

**Licence:** effectively public domain US government FOIA data.

---

## Running in parallel, not blocked by any of the above

- **The six-slide PDF**, due around 20 September. Needs an owner now
- **The family dictionary and gate table**, which is domain judgment rather than code and
  which the whole pipeline reads
