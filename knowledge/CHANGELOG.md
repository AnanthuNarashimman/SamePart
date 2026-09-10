# Change log

**Read this before making changes.** It records what was decided, what it replaced, why, and
what evidence forced the change. Git records who touched which line; this file records what
the change *meant*.

New contributors and coding agents: read [00-start-here.md](00-start-here.md) for context,
then this file for what has already been tried and rejected. Several entries below reverse
a decision in the original project document. **The original document is not the current
design.**

## How to add an entry

Newest first. Every entry needs: date, who, what changed **from → to**, why, and the
evidence. "It seemed better" is not evidence. If you reversed something in here, say so.

---

## 2026-09-10

### Redistribution: the one finding cross-organisation identity makes possible
**Who:** Aditya (with Claude) · beyond the eight named capabilities

`GET /api/analytics/redistribution`. One CPSE is sitting on stock another is about to buy.
Neither can see it today, because each describes the same item differently and their systems
have no way to know it is the same thing.

```
IN-31161600-0000011-4   BOLT, HEX HEAD; M10X80; A2-70; DIN931
  HOLDS  CPCL: 20 BOX-100 = 2,000 each, unissued 1,732 days
  BUYS   BPCL: 1,107/yr at Rs 218.84/each, 6 orders
  -> transfer 1,107, avoid Rs 242,225
```

30 opportunities, 17,386 base units that could move, Rs 20.2 lakh of purchasing avoided.

That one line does three things at once: it shows unit normalisation earning its keep
(20 boxes against 2,000 each), it names both parties, and it ends in an action rather than an
observation.

### Modelled stock rather than inferring it
A real material master carries quantity on hand; ours did not. Inferring "sitting unused"
from a gap in purchase history is a much weaker claim than reading the number.

Added `stock_on_hand`, `stock_base_qty` and `last_issue_date` through the model, the loader
and the header aliases, normalised to base units at ingestion exactly like price and quantity.
A holder's boxes and a buyer's each are therefore directly comparable, which is the
difference between a transfer recommendation and a nonsense one.

### Two numbers that would not have survived a stores manager
First run produced 150,000 bolts sitting in one depot, and annualised 25,000 units of demand
from a single purchase order. Both fixed:

- Stock is now drawn in **base units** at quantities a fastener store would actually hold,
  then expressed in the issuing unit. Previously it was drawn in issue units and multiplied up
- Demand is measured over the **actual purchasing window**, first order to last, and requires
  at least two orders. One order is a purchase, not a rate

Total fell from Rs 70.3 lakh to Rs 20.2 lakh. The smaller number is the real one.

### Four caveats ship inside the response
Stock is simulated here; idle is a strong signal, not proof the stock can move; freight,
condition and shelf life are not modelled so the figure is avoided purchase cost rather than
net saving; and quantities are compared in base units. They travel with the numbers rather
than sitting in a footnote someone can drop.


### Fictional vendors and sites, so a screenshot cannot be misread
**Who:** Aditya (with Claude)

The generator used **real supplier and installation names** alongside real CPSE names:
Sundram Fasteners, TVS Srichakra, Unbrako, Manali Refinery, Vindhyachal. Every price in this
project is invented, so attaching one to a named real company is a misrepresentation, and a
screenshot of the dashboard could reasonably have been taken for actual procurement data.

Replaced with coined names, each carrying a `(sim)` marker so it is unmistakable at a glance:

```
vendors : Anvil Fastener Works (sim), Trident Bolt & Nut Co (sim),
          Kestrel Industrial Supply (sim), Meridian Precision Fixings (sim),
          Quarry Head Fasteners (sim), Ironbark Industrial Traders (sim)
sites   : Refinery Unit 1-3 (sim), Power Station A-C (sim)
```

CPSE names stay as they are, because the problem statement names those organisations and they
already carry "(simulated)".

Swept the generated data, the sample upload and the generators: **no real company or
installation name remains.** Nothing else changed; the pipeline, the counts and the demo are
identical.


### Tool ready for the one real labelled dataset that exists
**Who:** Aditya (with Claude)

`python -m samepart.cli flis <REFERENCE.zip> <IDENTIFICATION.zip>` slices the US defence
logistics catalogue into a labelled evaluation set in our own import format.

**The download is manual and cannot be automated.** `dla.mil` returns 403 to scripted
requests and the archive APIs were unreachable from here. Verified, not assumed.

The tool streams both zips without extracting them, filters to threaded-fastener supply
classes, and keeps only items carrying two or more manufacturer part numbers, since an item
with one part number contains no pair to get right or wrong. Truth labels go to a separate
file so the pipeline cannot read the answer, and a `provenance.json` carrying the source,
licence and caveat ships beside the data so the numbers cannot travel without them.

This is the only public source with genuine "same item, different codes" ground truth. Every
benchmark that has real labels is consumer electronics; every Indian source has real text but
no labels.

### Note on the current dataset, for the record
Everything in `data/generated/` is produced by 375 lines in `backend/samepart/synth/`. There
is **no real CPSE data in this project and never has been.**

What is real inside it: the technical values. Thread diameters and pitches come from the ISO
261 and ISO 724 metric coarse series, property classes from ISO 3506 and ISO 898-1, and the
governing standards are genuine. Any single record is a bolt that exists.

What is invented: the prices (`rng.uniform(6.0, 190.0)` per material, then a random
0.82-1.34 multiplier per organisation), the descriptions, the house styles, and which
organisation holds what.

The only externally sourced file is the UNSPSC codeset, which is licensed personal-use-only
and gitignored.

**Outstanding:** the generator uses real company and plant names (Sundram Fasteners, Manali
Refinery) alongside real CPSE names. A screenshot could be mistaken for actual procurement
data, and implying a real supplier charged a fabricated price is a bad look. Organisation
names carry "(simulated)"; vendors and plants do not.


### Automation turned OFF by default, and the repository moved
**Who:** Aditya (with Claude)

`auto_merge.enabled` is now **false** in the family file. That is the posture the problem
statement describes, a workflow *allowing* users to review and approve, and an organisation
turns automation on deliberately having seen measured precision on its own data. It is also
the better demonstration, because the moment worth showing is a person approving a merge.

With it off, nothing is merged until someone approves, which left the dashboard empty. Added
`python -m samepart.cli baseline <reviewer> <keep_back>`: it works the queue as a reviewer
would, producing the prior review history a real deployment would already have.

**Every baseline approval is recorded against a named reviewer, not "auto".** The audit trail
reads `by_actor: {"steward-demo": 384}`, so what happened is visible rather than disguised.
It is a demo aid and the trail says so.

Result: 177 canonical materials on the dashboard **and** 25 merges still waiting, so there is
something real to approve on stage.

### The working directory is now the repository
Until now the project lived in an untracked folder and was copied into a clone by hand before
each push. That is exactly how a change goes missing. `/Users/adi/sih-2026` is now the git
repository itself, so `git status` is the truth and there is no copy step to forget.

Two things surfaced during the move, both worth knowing:

- The working copy's frontend was **stale**, several commits behind what Ananthu had pushed.
  Anyone editing it would have been working against old files
- `.gitignore` was rewritten. `data/` is ignored wholesale, which covers the generated
  catalogues, the scratch databases, and the **licensed UNSPSC codeset that forbids
  redistribution**. Also `.env`, `notes/`, and the original brief


### Every service is now live. Nothing returns fixtures.
**Who:** Aditya (with Claude)

`prevention` and `families` were the last two stubs and both are on the demo path.
`/api/health` reports eight live services.

**Check-before-create** reuses the exact cascade the reconciliation desk uses. No new
matching logic exists there, deliberately: if creation used different rules from review, a
material could be waved through at creation and flagged as a duplicate a week later, which is
how people stop trusting a system. Verified on four cases:

| Entered | Result |
|---|---|
| An exact duplicate of a loaded record | **blocked**, names the existing CPCL code |
| Same geometry, grade 12.9 instead of A2-70 | safe to create |
| Same geometry, grade not stated | **blocked**, asks for the missing attribute first |
| Genuinely new size | safe to create |

**Families** reads from the dictionaries at runtime and reports each family's classification.
`POST /api/families` loads a family from YAML at runtime, which is the live-bootstrap demo.

### A broad `except` was hiding a real fault
`settings` was never imported in the services module, so every use of it raised NameError,
which a bare `except Exception` swallowed as "the codeset is absent". Two features silently
returned nothing: classification paths in the export and in the families list. Both had been
shipping empty and neither had failed loudly.

Now a single helper checks whether the file exists, since the codeset is licensed and
gitignored and its absence is genuinely expected. Anything else raises.

Worth keeping as a lesson: the broad except was written to tolerate one known, legitimate
condition, and it swallowed an unrelated programming error for two features across two
commits.

### Demo posture
`SAMEPART_ALLOW_EXTERNAL=1` is set locally so the hosted model runs for demonstrations. The
committed default in `.env.example` stays **blocked**, and production runs an open-weight
model on CPSE infrastructure. See [14-deployment-and-sovereignty.md](14-deployment-and-sovereignty.md).

**One thing to fix before demonstrating:** the review queue shows `same_material=0`, because
auto-merge takes every unambiguous pair. There is nothing to approve on stage. Setting
`auto_merge.enabled: false` in the family file routes everything to a person, which is both a
better demo and the posture the PS actually describes.


### Egress guard and local model: the sovereignty claim, made checkable
**Who:** Aditya (with Claude) · **Prompted by:** "aren't we contradicting the data-must-not-
leave requirement with Azure?" — we were

**We were.** Two paths sent data out: extraction sent the raw description, and pairwise
comparison sent typed attributes. Never source codes, organisation names, prices, vendors,
purchase orders or spend, but specifications nonetheless.

**The default is now blocked.** Outbound calls are refused before they reach the network
layer, and turning them on is a deliberate act:

```
SAMEPART_ALLOW_EXTERNAL=0    # default
```

**Blocked calls are still recorded, and that is the point.** The ledger keeps the
destination, purpose, byte count, a SHA-256 digest and the exact payload, whether the call
went or not. A blocked entry lets an auditor read precisely what would have left the network
and confirm that it did not. "We are careful with your data" is not evidence. "Here is the
complete record, and nothing was sent" is.

Verified: the first blocked attempt withheld 3,518 bytes to a named host, with the payload
retained for inspection. `GET /api/governance/egress` serves it, with `blocked_only=true`.

### Everything still works with nothing leaving
Running with the default posture, no outbound calls at all:

| | |
|---|---|
| Records into canonical materials | 654 into 183 |
| Dead codes identified | 124 |
| Review queue | 3,019 pairs |
| Questions | 207 records |
| Migration plan | 124 to close, 296 to collapse |

The whole system runs on premises. The model tier is an enhancement to the 6.5% ambiguous
band, not a dependency.

### Local model client, preferred over the hosted one
Speaks the OpenAI-compatible endpoint that Ollama, vLLM, llama.cpp and LM Studio all expose.
It never touches the egress guard because nothing leaves the host.

`get_model()` prefers it whenever it is configured and reachable, regardless of what else is
available. **The hosted path is the fallback, not the default.** That ordering is the policy
expressed in code.

```
SAMEPART_LOCAL_MODEL=qwen2.5:7b-instruct
SAMEPART_LOCAL_MODEL_URL=http://localhost:11434/v1
```

`/api/health` now reports `runs_on_host` and `data_leaves_network` directly, so the answer to
the question is a field rather than an argument.

### What we can now say, precisely
The deterministic core runs entirely on premises and handles 93.5% of decisions. Outbound
calls are blocked by default and recorded when attempted. A local model is preferred when
present. On a 755,000-pair benchmark a distilled 14B open model scored 98.2 against GPT-4o's
99.0, so the on-premises path costs under a point of F1.


### Capability 7 second half: governance. All eight capabilities now covered.
**Who:** Aditya (with Claude)

The audit trail was already real, being append-only rows. Governance is the part that says a
national identifier is not something whoever ran the import gets to mint.

**Two-tier approval, and the reason is political rather than technical.** A CPSE will accept
its own steward deciding about its own codes. It will not accept another organisation's
steward, or a vendor's engineer, deciding that its code and someone else's are the same
thing. So a relationship inside one organisation is a local decision, and one that spans
organisations is the moment a national identifier comes into existence.

Verified on a live IOCL-to-BPCL pair:

| Role | Result |
|---|---|
| Steward of CPCL | 403 |
| Steward of IOCL, an organisation in the pair | **403** |
| Viewer | 403 |
| Administrator | 403 |
| National approver | 200 |

The refusal explains itself rather than saying "forbidden": *"This pair spans BPCL, IOCL.
Approving it creates a national identifier, which is not a decision one organisation makes
about another's codes."*

**Separation of duties.** The administrator may change the automation policy and the
dictionaries but may not approve a single mapping. Whoever sets the rules should not also be
the person who applies them.

### Reversibility, finally demonstrated rather than asserted
We have claimed all along that an incorrect merge is undone by deleting a cross-reference.
It is now implemented and proven.

Dissolving a three-CPSE cluster detached all three source codes, and afterwards:

```
CPCL-000002 still reads: HEX BOLT M8X16  10.9  DIN933  ZINC PLATED
IOCL-000003 still reads: Bolt, Hexagon Head, M8 x 16mm  Property Class CLASS 10.9
```

Untouched, because they were never altered in the first place. There was nothing to restore
and no data to recover. **This is the single strongest thing we can say against every
incumbent, all of which merge and delete inside the customer's own master.**

Two rules enforced: a reversal must carry a reason, recorded permanently; and a retired
national identifier is never reissued, because a number that has been quoted must never come
to mean something different later.

### Roles, and the default posture
`viewer`, `steward` (own organisation only), `national_approver`, `administrator`, declared
in `dictionaries/governance.yaml` with their permissions. Default state is
**review_everything**: automation stays off until an organisation turns it on having seen
measured precision on its own data. That matches the PS wording, which asks for a workflow
*allowing* users to review and approve.

New endpoints: `GET /api/governance`, `GET /api/audit`, and
`POST /api/canonical/{id}/reverse`. Refusals return **403 with an explanation**, not 500.


### Capabilities 5 and 8: migration support and ERP integration
**Who:** Aditya (with Claude) · both were sitting at zero

**The shape of the deliverable is the argument.** A cross-reference puts the CPSE's own code
in the first column and never alters it. Everything after it is additional information about
that code. Every competing approach merges and deletes inside the customer's master, which is
why those projects frighten plant teams and stall for years. This one adds rows.

```
org_code,source_code,national_code,canonical_identity,classification_code,...,status,duplicate_of
CPCL,CPCL-000002,IN-31161600-0000007-2,IN-0000007-5,31161600,...,duplicate,IOCL-000003
```

Four endpoints: cross-reference as JSON, the same as a downloadable CSV, a migration plan,
and an ERP payload.

### The migration plan, capability 5
| Action | Codes | Meaning |
|---|---|---|
| Keep | 183 | one per canonical material |
| Collapse | 298 | duplicates, **cross-referenced not deleted** |
| Close | 124 | no purchase order in four years |
| Review | 173 | the system would not decide alone |

**Do not quote the 65% headline.** Our generated data is deliberately duplicate-heavy, so
that figure is a property of the generator. The method is what transfers; the percentage is
not. Published duplicate rates sit nearer 7 to 9%.

Three notes ship with the plan itself, so they cannot be separated from the numbers: no CPSE
code is deleted, closing a dead code is a recommendation a stores team confirms, and codes
under review are ones the system declined to decide alone.

### The ERP payload, capability 8
Shaped as a **MATMAS05 IDoc**, which is the interface an SAP team already recognises, with
`E1MARAM` for basic data, `E1MAKTM` for descriptions and `E1MARMM` for alternative units,
correctly carrying the conversion factors normalisation produced (`BOX-100` = 100 `EA`).

Our addition is a `Z1XREFM` segment holding each CPSE's **unchanged** source material number
beside the national code. That segment is the whole proposition in one place: the national
reference is added, the local code is untouched.

Nothing talks to a real SAP system. The point is that the output arrives in a shape a systems
team can wire up rather than one they need talked through.


### The model tier, second half: pairwise comparison
**Who:** Aditya (with Claude) · **Completes:** capability 1's "AI-based matching"

Tier 3 of the cascade. It sees **typed attributes with their evidence, never raw text**, so
it is comparing established facts rather than guessing at similar-looking strings.

**Only 224 of 3,429 pairs reach it, which is 6.5%.** The rest are settled by rules, or are
missing a value no model can invent. Routing a pair whose critical attributes are absent
wastes a call and invites a fabrication, so `needs_model` excludes them.

Three constraints, all deliberate:

1. **A model verdict is never auto-merged**, whatever the automation policy says. Automation
   is permitted only where nothing is being judged, and a model call happens precisely
   because something is. This is what keeps the PS's user-validation requirement satisfied
   now that inference is in the pipeline
2. **The gates run again over the model's answer** and can overrule it
3. **It must name the deciding attribute.** A verdict citing no known attribute is rejected,
   because "they look alike" is the reasoning this system exists to replace

Unprompted, it got the asymmetry right on strength classes: 10.9 may replace 8.8, but 8.8
must never replace 10.9.

### A prompt bug that halved accuracy, and what it teaches
First measurement on the ambiguous band: **40%**, worse than useless.

Every error was the same shape. One record states a finish, the other is silent, and the
model answered insufficient_evidence because finish is "critical".

**The model was following my instruction faithfully. The instruction was wrong.** We had
carefully separated two questions in the dictionary — does a *difference* mean different
materials, and must the value be *known* to decide at all — and then I wrote a prompt that
said only "critical" and let both collapse into one.

After telling the model which attributes are identity-bearing and which must be known,
separately:

| | Agreement with ground truth |
|---|---|
| Rules alone on this band | 40% |
| Model tier, original prompt | 40% |
| **Model tier, corrected prompt** | **84%** |

Same model, same data, same 25 pairs. The lesson worth keeping: when a model underperforms,
check whether the prompt contradicts the system's own semantics before concluding anything
about the model.

Cost on the band: about 2 seconds and roughly 700 tokens per pair.


### The model tier, first half: extraction. And it abstains.
**Who:** Aditya (with Claude) · **Closes:** the "no NLP anywhere" exposure

Model access sits behind one interface, so swapping the hosted deployment for an open-weight
model inside a CPSE's own network is configuration, not a rewrite. With nothing configured
the pipeline degrades to the deterministic path, which is also why an API outage cannot
break the demo.

Extraction runs **only on attributes the patterns left unknown**, so cost tracks difficulty
rather than volume.

**The result that matters most in this project so far.**

Our generated blanks are unrecoverable by construction: the generator removed the value from
the description entirely. A model that fills them is hallucinating. Across 30 records and
**122 attributes with no answer present, the model abstained 122 times. Zero inventions.**

And where the answer *is* present but the patterns cannot read it, it recovers:

| Text | Patterns read | Model read |
|---|---|---|
| `NOM 20 LEN 80 10.9 AS PER ISO 4014` | nothing | diameter 20, length 80 |
| `BLT HX HD DIA.24/LG.70 GR 12.9 HDG` | nothing | diameter 24, length 70, head HEX |

**Two guards make this trustworthy rather than plausible.** The prompt states that an unknown
is useful and a guess is dangerous, because a fabricated property class on a pressure-joint
bolt is a safety problem. And every value must quote the exact substring that proves it,
checked against the source before anything is written, so a confident invention cannot enter
through this door.

### Why it does not run inline
A call takes about two seconds, so enriching 654 records would add twenty minutes to an
import that currently finishes in under one. It runs as its own pass over only the records
that have blanks: `python -m samepart.cli enrich [n]`.

Anything it fills is stored with method `llm` and its evidence, so a reviewer always sees
that a machine inferred this rather than a pattern reading it outright.

### Honest note on our own numbers
Running enrichment over our data fills **nothing**, and that is the correct outcome, not a
failure. The blanks in the generated catalogue genuinely have no answer in the text. On real
material master records, which carry long text, classification characteristics and purchase
history alongside the short description, the recovery cases above are the ones that would
apply. **Do not claim the model reduces our 207 open blanks. On this data it cannot, and
saying so is the point.**


### Capability 4: the Common National Material Code is no longer a counter
**Who:** Aditya (with Claude)

**From:** `SMP-000417`, a bare sequence with no structure, no validation and no owner.
**To:** a structure following the precedent **India already participates in.**

Under the NATO Codification System, which India joined on 10 June 2008 as a Tier-1 member
with country code 72, a stock number is a classification prefix plus a permanent item
identification number, and the rule that matters is that **the identification number never
changes even when the item is reclassified.**

We apply the same rule, and it forced a design correction. The first version put the
classification inside the primary key, which meant reclassifying a material would change its
key and drag every foreign key with it. That is precisely what the NSN design avoids. So:

| | |
|---|---|
| **Stored identity, permanent** | `IN-0000417-6` |
| **Printed national code** | `IN-31161600-0000417-3` |
| After reclassification | `IN-31161500-0000417-4` |
| Identity | **unchanged** |

Everything keys on the identity. The full code is derived for printing and quoting.
Reclassification becomes a metadata change rather than a migration, which is what lets a
CPSE trust a code it has printed on a bin label and quoted in a purchase order.

**Check digit.** Luhn, catching every single-digit slip and most transpositions. A mistyped
code is rejected with what the digit should have been, rather than silently resolving to
nothing. This matters for an identifier humans read aloud across organisations.

**Governance is written down**, in `dictionaries/national_code.yaml`, because "who owns this
identifier" is the first question a CPSE asks and the answer cannot be "whoever ran the
import". Proposed authority is a national codification cell, with the honest note that the
Directorate of Standardisation already performs exactly this function for defence materiel
and extending an existing statutory body is a shorter route than creating one. Five rules
are recorded, including that serials are never reused and a CPSE's own code is never altered.

The format is declared as data, so changing the prefix, widths or check-digit policy is a
file change.

### Not a regression: the CLI was reporting the wrong thing
After wiring imports to trigger matching, the seed output appeared to show auto-merges
collapsing from 389 to 20. The database was fine at 408. Imports now do the matching for the
rows they bring in, so the final pass finds almost nothing left and was reporting only its
own remainder. Added `cli summary`, which reports the **state of the database** rather than
the state of the last pass.


### Capability 2 second half: classification into a taxonomy
**Who:** Aditya (with Claude) · **Closes:** "intelligent classification and categorization"

Two tiers, and the first is not machine learning.

**Declared anchor.** A family file states its class outright. `hex_bolt` declares UNSPSC
`31161600`, which is Manufacturing Components and Supplies > Hardware > Bolts. Once
extraction has decided a record is a hex bolt, its class is **known, not inferred**.
Every canonical material is now classified this way.

**Text inference** for anything the first tier cannot place. Rarity-weighted overlap against
node titles, using each node's full ancestor context.

### Three bugs found by testing rather than reading
- **Top-down search was wrong.** A description shares no vocabulary with a segment title
  like "Manufacturing Components and Supplies", so the walk died at level one and returned
  nothing. Terminals are now scored directly and the path read off the code
- **No stemming.** The taxonomy says "Bolts", a description says "BOLT". Nothing matched
- **Scoring let unknown words in free.** A word absent from the taxonomy has an IDF of zero,
  so it cost nothing, and a description of mostly part numbers scored a **perfect 1.0**
  against a telephone splitter off the single word "plain". Now cosine-normalised with a
  penalty for unknown terms

### Two design decisions worth keeping
**Classify the extracted noun phrase, not the raw description.** Raw text fails twice:
"BLT HEX HD" contains no word the taxonomy knows, and in "PLAIN WASHER M16 STAINLESS" the
material word outranks the item noun and lands it under steel alloys. Extraction already
worked out what the thing is.

**Scope the search to plausible segments.** Unscoped, "NUT HEXAGON" classifies under
agricultural nut production. This is a real, well-known failure of general taxonomies on MRO
text, and scoping is what production tools do. It is still wrong for "nut", which the
declared anchor is the answer to.

### On accuracy: what we can and cannot claim
A held-out test over 232 class titles, reworded and shortened, gave 97.8% at segment, 97.0%
at family and 94.8% at class.

**Do not put those numbers on a slide.** The test is circular: the queries were built from
the class titles themselves, so it measures titles matching titles. Published work
(arXiv:2503.04728) reports roughly 90% coarse and 80% at depth on **real product
descriptions**, which is a far harder task, and our figure is not comparable to it.

What is honestly claimable today: classification is implemented, the declared anchor is exact
and covers every record whose family is known, and the inference tier is a lexical baseline
that has not been tested on real descriptions because we have no labelled ones. The model
tier and reviewer confirmations as labels are what would make it a genuine trained artifact.

### Codeset limitation, worth knowing
The free UNSPSC extract has 58 segments, 452 families, 2,139 classes and 10,676 commodities,
but **26% of classes carry no commodity detail and our entire fastener domain is in that
26%**. Class level is the deepest reachable for bolts, screws, nuts and washers.

The file is licensed **personal use only and forbids redistribution**, so it is gitignored
and never committed. A national deployment needs a licensed or government-issued codeset.
Because the taxonomy is loaded as data, swapping it is a file change.


### Column mapping detects itself
**Who:** Aditya (with Claude) · **Asked for by:** Ananthu, who did not want to click every
column by hand

New `POST /api/imports/preview`. Upload a file and it returns the headers, five sample rows,
a proposed column mapping with a confidence per field, and whether the required columns were
all found. Nothing is imported. Send `column_map` straight back to `POST /imports`.

Header synonyms live in `dictionaries/column_aliases.yaml`, **as data**, for the same reason
value synonyms do: the person who knows that `MAKTX` is the short description is a domain
person, not a developer.

Verified on three real header styles, all mapping with no human input:

| Style | Example headers | Result |
|---|---|---|
| Our sample | `source_code, description, uom` | 7 of 7 exact |
| SAP export | `MATNR, MAKTX, MEINS, MENGE, NETPR` | 6 of 6 exact |
| Hand-made sheet | `Material Code, Item Description, Qty, Rate, Make` | 7 of 7 exact |

A file missing a required column returns `ready: false` and names what is missing, rather
than failing after the upload.

**For the UI:** call preview on file selection, pre-fill the mapper from `column_map`, and
only ask about fields where confidence is below 0.9 or the column is null. Longest field
names are matched first, so "manufacturer part number" claims its column before plain
"manufacturer" can take it.


### Import reported success as failure
**Who:** Aditya (with Claude) · **Found by:** Ananthu, whose upload "failed" when it had not

Re-importing a file put one line per already-seen row into the `errors` list. A correct,
idempotent, successful import therefore came back with nineteen errors and looked broken.

`ImportStatus` now separates three things:

- `errors` — things that went **wrong**. An empty list means the import succeeded
- `warnings` — things worth knowing that are **not failures**, such as rows skipped as
  already present
- `rows_skipped` — a count, so the UI can say "19 already present" instead of listing them

Re-importing the same file is safe and changes nothing. **The UI must render warnings
differently from errors**, or this reads as a failure again.

Additive change, so nothing on the frontend breaks.

### Sample upload file for demos
`samples/HPCL_sample_upload.csv`. Nineteen rows written in a fifth house style, deliberately
colliding with data already loaded: one that matches the M16x80 cluster, one grade conflict,
one with the grade missing, one A4 against an existing A2, and one carrying a manufacturer
and part number. Upload as org `HPCL`, family `hex_bolt`.

### Import now triggers matching automatically ✅ (was a known gap)
Ingestion runs the matcher immediately, **scoped to the rows that just arrived**. The new
records still compare against the whole corpus, but the thousands of pairs already decided
are not recomputed. That is also how it would run in production: a full rebuild is a
migration, not a daily operation.

Uploading 19 rows compared 269 pairs rather than 3,698, auto-merged 35, queued 104, and
returned in **165 ms**. No manual `cli match` step, and the queue reflects the upload
immediately.

`ImportStatus` gained `candidate_pairs`, `auto_merged`, `queued_for_review` and `matched_at`
so the import screen can say what the upload actually did rather than just "completed".


### Frontend integration guide added
**Who:** Aditya (with Claude) · **For:** Ananthu and any agent working on the UI

[`BACKEND_FOR_FRONTEND.md`](../BACKEND_FOR_FRONTEND.md) at the repo root. Every endpoint with
a **real captured response** rather than an illustration, which services are live against the
database and which still return fixtures, how to run and seed the backend, and how to
generate types from the published schema.

Four things in it are not obvious from the schema and will otherwise be got wrong:

- **`unit_price` and `unit_price_base` are different numbers.** A box of a hundred costs
  4,180 and each costs 41.80. Comparing the wrong one is a hundredfold error in a figure
  someone reads off a slide
- **The question screen is one card per record, not one row per pair.** 689 deferred pairs
  are 207 records. Designing it per pair triples the apparent work and misleads the reviewer
- **`status: "unknown"` rows must be rendered, not hidden.** The blank is the reason the
  system is asking
- **The withheld savings figure belongs on screen**, next to the claimed one. Money we
  deliberately do not claim, because those merges are under audit, is the point rather than
  a footnote

Live now: catalogue, review, questions, analytics. Still fixtures: prevention, families.
Stub and live share shapes exactly, so either can be built against.


### Capability 6 is live: dashboard analytics, on real spend
**Who:** Aditya (with Claude) · **Flips:** `analytics_service`

Four views, all computed from purchase orders rather than a price column.

| Figure | Value |
|---|---|
| Records into canonical materials | 654 into 181 |
| Duplicate rate | 44.3% (synthetic, by construction) |
| Dead codes, unordered in four years | 124 (19.0%) |
| Duplicate codes that could collapse | 290 |
| Spend analysed | Rs 29.0 crore, 1,418 PO lines |
| Materials bought by more than one CPSE | 180 |
| **Aggregation opportunity claimed** | **Rs 3.91 crore on Rs 20.3 crore shared spend (19.3%)** |
| Opportunity withheld, merges under audit | Rs 78.6 lakh across 6 clusters |

New endpoints `/api/analytics/rationalisation` (capability 5) and
`/api/analytics/audit-flags`. Nothing already in the contract changed shape, so nothing on
the frontend breaks.

### We do not claim money from merges we do not trust
The top savings cluster was one of our own **false merges**. Its Rs 53 lakh of "opportunity"
was two different materials priced differently, which is our error wearing a suit.

Savings now excludes any cluster the audit check has flagged, and reports the withheld
amount separately. **Rs 78.6 lakh is deliberately not claimed.**

This matters more than the arithmetic. A judge who asks how two CPSEs could pay 32 times
different for one bolt gets the answer "they could not, and that is why we excluded it,"
instead of the answer "because our system made a mistake."

### The false-merge detector, measured
| | |
|---|---|
| Clusters flagged | 6 |
| Genuinely wrong | 6 |
| **Precision** | **100%** |
| Recall | 50% (missed 6 of 12) |

**It is a screening tool, not a proof.** A flagged cluster is worth a human look. An
unflagged one is not proven correct. Say it that way; the recall number is half and
pretending otherwise is the kind of claim that unravels under one question.


### Procurement history is now a first-class input
**Who:** Aditya (with Claude) · **Why:** the PS names it — "material codes, descriptions,
specifications, technical parameters **and historical procurement data**"

New `procurement_line` table, loader and ingestion, seeded with 1,418 purchase order lines
across four CPSEs over four years, Rs 29.0 crore of spend. Quantities and prices are
normalised to base units at the boundary, exactly as master records are, because one box of
a hundred and a hundred each must be comparable before any aggregation is valid.

It earns its place three times, as predicted:

**Capability 5, legacy rationalisation.** 124 of 654 material codes have no purchase order in
four years. **19% of the master is dead weight.** That list cannot be produced without
procurement history, and it is exactly what "legacy material code rationalisation" means.

**Capability 6, analytics.** 142 canonical materials are bought by more than one CPSE, which
is what demand aggregation needs to be real rather than hypothetical.

**Capability 1, matching evidence.** 177 vendor part numbers appear against more than one
CPSE material code. That is identity evidence the description alone cannot give, and it is
independent of how either organisation worded anything.

### Unplanned finding: price variance detects our own false merges
Investigating implausible price spreads (625%, 685%, 3186%) showed they were not price
variance at all. **All three were clusters where we had merged two genuinely different
materials.**

| | Median price spread | n |
|---|---|---|
| Correctly merged clusters | **1.40x** | 165 |
| Falsely merged clusters | **2.34x** | 12 |

12 of 181 canonical materials contain more than one true identity, which is 6.6%.

This gives the system an **independent audit signal on its own merges**. Procurement history
plays no part in making a merge, so a cluster whose price spread is far above the norm is a
merge worth a second look, flagged by evidence the matcher never saw. That directly serves
capability 7, governance, and the PS's user-validation requirement, because the system can
nominate its own suspicious decisions rather than waiting to be caught.

Also worth noting for the money slide: **1.40x is the credible spread number**, not the
headline extremes. Quoting 3186% would be quoting our own bug.


### Human workload cut from 446 actions to 288, by policy rather than by tuning
**Who:** Aditya (with Claude) · **Prompted by:** "is a person answering 207 records viable?"

Three additions, all declared as data so a domain owner controls them.

**Auto-merge policy** (`auto_merge` in the family file). The system merges without asking
only when there is nothing to judge: every comparable attribute agrees exactly, every
attribute that must be known is known, and no gate had to intervene. **389 pairs merged
automatically**, creating 184 canonical materials covering 471 source codes, with no human
involved. One in twenty is still routed to a person, because an automation rate nobody
audits is a claim rather than a control.

**Unresolvable blanks** (`POST /api/records/{id}/unresolvable`). Some answers do not exist:
the drawing is lost, the supplier has gone. Marking a blank unobtainable stops it being
asked forever, and the affected pairs reach a final state, which is separate identities
where the other record states a conflict-critical fact. Without this the queue is permanent,
because every run re-proposes the same pair and re-asks the same unanswerable question.

**Stopping curve** on `GET /api/questions`. Answering in ranked order, 10 answers clear 19%
of the deferred pairs, 50 clear 51%, 100 clear 74%. Shown so a data owner stops early **on
purpose** rather than feeling obliged to empty a queue.

| Outcome | Pairs | Human actions |
|---|---|---|
| different, auto-rejected | 1,893 | 0 |
| auto-merged, nobody asked | 389 | 0 |
| audit a sampled auto-merge | 20 | 20 |
| confirm a substitute group | 438 | 61 |
| open a record, fill blanks | 689 | 207 |
| **Total** | **3,429** | **288** |

288 actions is 8.4% of pairs and 0.44 per record, down from 446 and 13.0%.

**What is left is genuinely irreducible without more data.** 207 record blanks exist because
nobody wrote the grade or finish down; no algorithm invents information that was never
recorded. The model tier in step 4 should recover a large share, because it can read the
whole source record rather than the 40-character short description our regex reads. The 61
substitute confirmations are engineering judgement and should stay with a person.

**Honest scale note.** At 32% of records needing a blank, a 400,000-line master implies about
128,000 questions, roughly 200 working days for one person. That does not scale as-is. The
fixes are the model tier reading richer fields, the stopping rule, and accepting that some
blanks stay unresolved. Do not present the demo ratio as a rollout plan.

### Bug found and fixed while testing the escape hatch
Marking a blank unobtainable initially left 18 of 20 pairs as *possible alternative*, because
a later gate downgraded the separation into a substitution proposal. That moved work between
queues instead of closing it. An unobtainable value now ends the question: it can never be
softened back to same or alternative.


### Grouped question view: the queue as a person actually experiences it
**Who:** Aditya (with Claude) · **Prompted by:** "isn't 689 pairs a lot?" — it was the wrong
denominator

New `GET /api/questions` and `POST /api/records/{id}/answer`, behind their own
`QuestionService` protocol so they stay separable from the review queue.

**The queue holds pairs. A reviewer does not answer pairs.** The same record appears in many
blocked pairs and one answer clears all of them.

| | Count |
|---|---|
| Deferred pairs | 689 |
| Distinct blanks behind them | 228 |
| **Records a person opens** | **207** |

Only two attributes cause every deferral: **finish** and **grade**. Nothing else. Answering
the fifty highest-value blanks clears half the queue; a hundred clears three quarters.

Questions are ranked by how many pairs each answer unblocks, and each blank shows what the
counterpart records say for that field, so the reviewer answers with context instead of
blind. Verified live: answering one record re-decided 21 pairs immediately.

### The real human workload, measured
The honest number is **not** one action per pair.

| Verdict | Pairs | Human actions | What the action is |
|---|---|---|---|
| different | 1,893 | **0** | auto-rejected, informational only |
| same_material | 409 | **178** | approve one cluster, not one pair |
| possible_alternative | 438 | **61** | confirm one substitute group |
| insufficient_evidence | 689 | **207** | open a record, fill one or two blanks |
| **Total** | **3,429** | **446** | **13% of pairs** |

Merge clusters are mostly small: 92 pairs of two, 60 of three, and the largest is seven
records across four CPSEs.

**Step 5 is what cuts this further.** A calibrated auto-merge threshold removes most of the
178 cluster approvals, because a cluster where every attribute agrees exactly does not need
a person. The 207 record blanks are irreducible: nobody wrote the grade down, so somebody
has to say what it is.

**This is also a product, not just a cost.** The system hands a data owner a ranked worklist
saying "these 207 records are missing a grade or a finish, start with this one because it
unblocks twenty comparisons." That is the same shape as the missing-synonyms report, and it
is worth saying out loud in the pitch.

### Considered and rejected: relaxing the finish rule
Exempting finish from the asymmetric-unknown rule saves 210 deferrals and **triples false
merges**, from 32 to 102. In a refinery that is the wrong direction. Recorded so nobody
re-runs it.


### Step 2 of the build plan is live: matching and the review queue
**Who:** Aditya (with Claude) · **Flips:** `review_service`

3,429 candidate pairs decided over 654 real records, eliminating 98.39% of comparisons.
**No model call anywhere in this path.** Blocking plus deterministic rules do all of it, so
an API outage cannot break the demo.

The cascade is four tiers, cheapest first, and every decision records which tier made it:
identity on manufacturer plus part number, then attribute agreement, then a model tier
(step 4), then the conflict gates, which are a **veto** rather than a fallback and run on
every pair regardless of who decided.

Reviewer actions are wired end to end. Approve merges into a registry-minted canonical
identity, or links a conditional substitute, or records a confirmed difference. Reject
always writes a cannot-link constraint, so a rejection is never re-proposed. Supplying a
missing value re-runs the cascade immediately and stores the answer with method `given`, so
the audit trail distinguishes what a machine read from what a person asserted.

Survivorship is settled, closing [09](09-open-decisions.md) #8: **no winning record is
chosen.** The canonical description is synthesised from the union of evidenced attributes,
and conflicting values are retained on the canonical record rather than silently dropped.

### Attribute modelling: one setting split into two questions
**Who:** Aditya (with Claude) · **Found by:** measuring against labels, not by inspection

Every false merge in the first measurement was a pair differing only in **finish** or
**governing standard**. The dictionary marked finish informational, so a difference never
blocked. In real stores practice a zinc-plated bolt and a plain one are different stock
items.

Making finish critical fixed precision and destroyed recall, which exposed the real problem:
`criticality` was answering two different questions at once. They are now separate.

- `criticality` — if these DIFFER, does that make them different materials?
- `required_for_decision` — must this be KNOWN before anything can be decided?

Finish is critical but not required: a different finish means a different stock item, while
a finish nobody wrote down does not make the pair undecidable.

A third rule followed from the same measurement. If a conflict-critical attribute is stated
on one record and absent on the other, that is **not agreement**, it is an open question,
and it now defers to a human. Both sides silent is fine, since neither record claims
anything.

### Measured trade-off, recorded so nobody re-runs it
Same data, same code, four dictionary settings.

| Setting | Precision | Recall | F1 | False merges | Human queue |
|---|---|---|---|---|---|
| finish informational | 81.4% | 88.2% | 84.7% | 118 | 680 |
| finish critical and required | 94.1% | 59.9% | 73.2% | 22 | 725 |
| finish critical, not required | 83.5% | 88.2% | **85.8%** | 102 | 479 |
| **+ asymmetric unknown defers (current)** | **92.2%** | 64.3% | 75.8% | **32** | 689 |

**In every configuration, zero true duplicates were called "different."** Misses always
become "needs input". The system does not get it wrong quietly; it defers.

We ship the last row deliberately. F1 is not the objective here. A false merge in a refinery
is a safety incident, while a deferred pair costs a reviewer a minute. Currently 79.9% of
pairs are auto-decided and 689 reach a human.

**This is a dial, and it lives in the dictionary.** A domain owner tunes the
safety-versus-throughput balance per attribute without touching code. Step 5 replaces the
guesswork with a calibrated coverage-against-risk curve.


### Step 1 of the build plan is live: ingestion
**Who:** Aditya (with Claude) · **Flips:** `catalogue_service` from stub to live

`/api/orgs` and `/api/imports` now read and write the database. 654 records across four
simulated CPSEs ingested end to end, 6,540 attributes extracted with per-field evidence.

Three things worth knowing about how it works.

- **Column mapping is configuration per source, never a hardcoded parser.** Every CPSE
  exports different headings for the same facts
- **Units are converted at the boundary.** A price of 1,550.85 per hundred is stored as
  15.51 per each. Nothing downstream ever sees an unnormalised price, which is what makes
  the later price-variance and aggregation views valid
- **Unknown attributes are stored, not omitted.** A missing critical attribute is the reason
  the system asks a question, so it has to survive into the database and onto the screen

Also handled: re-importing the same file skips already-seen source codes rather than
duplicating, and a file without the required columns fails with a message naming the columns
it actually found.

Seed the database with `python -m samepart.cli seed` and inspect it with `... cli stats`.

### Services can now be live and stubbed at the same time
**Who:** Aditya (with Claude)

`SAMEPART_MODE=live` flips only the services that have a live implementation; the rest keep
returning fixtures in the same shape. `/api/health` reports which are real, so the frontend
can see progress without asking. **Verified:** catalogue served from the database while the
review queue still served fixtures, in the same process.

### Dictionary gains value synonyms, not just field-name aliases
**Who:** Aditya (with Claude) · **Found by:** measuring extraction, not by inspection

**From:** attributes carried `aliases`, which are synonyms for the *field name*.
**To:** attributes also carry `value_aliases`, mapping a wording seen in source text to the
canonical value.

**Why:** 62% of finishes came back unknown. The enum listed `ZINCPLATED` and
`HOTDIPGALVANISED`, but real descriptions say "self colour", "electro galvanised", "HDG",
"ZP" and "pickled and passivated". Field-name aliases do not help with that at all.
After recording the synonyms, unknown finishes fell to 28%, which matches the generator's
own drop rate almost exactly. Longest surface form wins, so "hot dip galvanised" beats a
bare "galvanised".

**This is a domain-owner job, not a developer one.** Value synonyms are exactly the kind of
knowledge a plant engineer has and a programmer does not, and they live in the YAML.

Remaining unknowns are all legitimate: thread pitch is never written in these descriptions,
and manufacturer, part number, grade and standard are absent from the source at the rates
the generator was told to omit them.


### Backend shape: one application → routers over a swappable service layer
**Who:** Aditya (with Claude)

**From:** a single application module owning HTTP, business logic and data access together.

**To:** three separated layers.
- `api/routers/` — one small router per concern (catalogue, review, prevention, analytics,
  families). HTTP only: parse, validate, delegate, return
- `services/protocols.py` — a protocol per concern, which is the only thing routers depend on
- `services/stub.py` — fixture implementations, selected in `api/deps.py`

**Why:** each endpoint can move from stub to live **independently**, touching one file, with
no change on the frontend. A monolithic handler would force an all-at-once cutover and make
the stub work throwaway. It is not.

**How to go live on one endpoint:** write the real implementation, satisfy the protocol,
change the one line in `api/deps.py` that returns it. Nothing else moves.

### Stub API shipped so the frontend is not blocked
**Who:** Aditya (with Claude) · **Unblocks:** Ananthu

Every endpoint in [11-team-split-and-stack.md](11-team-split-and-stack.md) §4 now responds,
returning the **five seeded demo cases** rather than placeholder text, so what gets built
against the stubs is what gets demonstrated.

Verified live: queue returns groups ordered `needs_input` first per
[10-frontend-plan.md](10-frontend-plan.md); match detail carries per-field evidence and
renders `unknown` explicitly; approve returns a canonical id and states that both source
codes are retained; unknown match returns 404; unknown queue group returns 400.

Run it with `uvicorn samepart.api.app:app`, generate types from `/openapi.json`. Mode is
reported at `/api/health`.

### `api/schemas.py` is now the single source of truth for the contract
**Who:** Aditya (with Claude)

Frontend types are generated from the published OpenAPI schema. **Nobody hand-writes the
other side's types**, because hand-written types drift silently. Changing a field here
changes the frontend on its next generation, which is why contract changes are a
conversation first.

### Dependencies: sentence-transformers and PyTorch removed
**Who:** Aditya (with Claude) · **Follows:** the retrieval measurements below

Roughly 2.5GB of dependency for zero measured gain. `pipeline/embeddings.py` and the
`Embedder` injection point remain, defaulting to `None`, so a model can be reintroduced in
one line **if a measurement justifies it**. Added `python-multipart`, required by FastAPI
for the file upload on the import endpoint.


### Retrieval architecture: text similarity → attribute blocking with lexical fallback
**Who:** Aditya (with Claude) · **Reverses:** original plan §3 and §5, "candidate retrieval
via embeddings"

**From:** embed the raw description, take top-k nearest neighbours by cosine similarity.

**To:** two tiers. Tier 1 blocks records exactly on the family's declared primary key
(diameter and length for hex bolts). Tier 2 handles only records whose primary key could not
be extracted, using rarity-weighted word overlap over the canonical form **plus** the raw
text.

**Why:** measured on the 654-record generated catalogue.

| Method | Pairs completeness | Candidate pairs |
|---|---|---|
| Embed raw description | 7.8% | 8,444 |
| Embed raw + plain word overlap | 29.4% | 8,020 |
| Embed canonical form | 97.1% | 8,038 |
| **Block on extracted diameter and length** | **100%** | **3,429** |

Embedding raw descriptions failed because a general sentence model clusters records by the
**house style of whoever wrote them**, not by what the part is. Every record's nearest
neighbours came from its own organisation. Blocking beat every text method on both recall
and candidate count, with no model at all.

### Embedding model: Azure text-embedding-3 → BAAI/bge-base-en-v1.5 → not used at all
**Who:** Aditya (with Claude)

**From:** a hosted Azure embedding deployment. **Then:** a local sentence transformer, chosen
to make the on-premises claim real. **Now:** no neural model in the retrieval path.

**Why:** with attribute blocking doing the work, the embedding contributes nothing measurable.
On the stress test where dimensions were reformatted into styles the regex misses, lexical
matching alone scored 88.1%; adding the embedding scored 88.1%; using the embedding alone
scored 81.7%.

**Consequence:** `sentence-transformers` and PyTorch are roughly 2.5GB of dependency for zero
measured gain. The `Embedder` interface stays as an optional injection point, defaulting to
`None`. **Do not add an embedding model back without a measurement showing it helps.**

**Also relevant to the pitch:** the resource has five chat deployments and no embedding
deployment. This removes that blocker entirely, and it means retrieval never sends a
description off the machine.

### Tier 2 fallback: canonical form only → canonical form plus raw text
**Who:** Aditya (with Claude)

**Why:** canonicalisation is built from the same regex extraction that just failed, so on its
own it strips out exactly the numbers a fallback record still needs. Keeping raw tokens
alongside preserves them, and rarity weighting suppresses filler words automatically.
Measured 77.1% → 88.1% pairs completeness.

### Blocking strategy moved into the family dictionary
**Who:** Aditya (with Claude)

Added a `blocking` block to `hex_bolt.yaml` declaring `primary_key`, `fallback` and
`fallback_top_k`, validated at load time. **No material family is named anywhere in the
code.** This is what makes the live new-family bootstrap demo possible, per
[08-ranked-additions.md](08-ranked-additions.md) #12.

### Regex patterns corrected
**Who:** Aditya (with Claude)

Three fixes, each found by a failing case, not by inspection:
- Diameter and length now parse the `DIA 16MM; LG 80MM` house style, not only `M16X80`
- Length lost its trailing word-boundary anchor, which silently failed on `M16X80MM`
  because the digit is followed immediately by a letter
- Grade accepts `A2 70` with a space, not only `A2-70`

All four simulated house styles now produce an identical canonical form.

### Table and verdict names aligned to the frontend plan
**Who:** Aditya (with Claude) · **Aligns with:** Ananthu's
[10-frontend-plan.md](10-frontend-plan.md)

| From | To |
|---|---|
| `candidate_pair` | `candidate_match` |
| `canonical_mapping` | `approved_mapping` |
| class `CandidatePair` | `CandidateMatch` |
| class `CanonicalMapping` | `ApprovedMapping` |
| verdict `same` | `same_material` |

`known_conflict`, `possible_alternative` and `insufficient_evidence` already matched.
**The frontend plan is the naming authority.** Backend follows it.

### Evaluation bug, found and fixed
**Who:** Aditya (with Claude)

Ground-truth pairs were built in list order while candidate pairs were built sorted, so any
pair whose two codes were not already alphabetical counted as a miss. **Every recall number
measured before this fix was understated by roughly a third.** Attribute blocking read 65.7%
before the fix and 100% after.

Recorded because it is the kind of error that silently makes a good design look bad. If a
retrieval number looks implausibly low, check the pairing before changing the architecture.

### Python 3.9 → 3.12
**Who:** Aditya (with Claude)

macOS ships Python 3.9, which cannot run pydantic v2's type evaluation. The project virtual
environment is built on Homebrew's 3.12, and `/opt/homebrew/opt/python@3.12/libexec/bin` was
prepended to `PATH` in `~/.zshrc`. Apple's system interpreter at `/usr/bin/python3` is
untouched.

### Azure credentials moved out of the shell profile
**Who:** Aditya (with Claude)

The API key was in `~/.zshrc`, which exposes it to every process. Moved to the project
`.env`, permissions `600`, already gitignored. **Never commit `.env`.**
Config: endpoint `jairelan2005-6346-resource.cognitiveservices.azure.com`, API version
`2024-12-01-preview`, chat deployment `gpt-5.6-terra` (verified live).
Other deployments available: `gpt-5.4`, `grok-4.3`, `gpt-5.6-sol`, `gpt-5.6-luna`.

### Knowledge base created
**Who:** Aditya (with Claude) · files 00 through 09, plus this log
**Who:** Ananthu · file 10, the frontend plan

---

## Standing decisions that must not be quietly reversed

These were each argued and settled. Reversing one is fine; doing it without an entry here is
not.

1. **Families, attributes, units, gates and blocking are data, not code.** A new family is a
   new YAML file
2. **Conflict gates sit outside the model and can veto it.** They are never a model call
3. **Source codes are never overwritten.** A canonical identity is an additional row, so an
   incorrect merge is undone by deleting a cross-reference
4. **Decisions are append-only.** The audit trail is the table, not a report
5. **Canonical IDs come from a registry, never from a language model**
6. **Extraction may output `unknown`.** A missing critical attribute is why the system asks a
   question instead of guessing
7. **Retrieval proposes, it never decides.** Embeddings and lexical overlap rank candidates;
   only typed attributes and gates determine a verdict
8. **Report synthetic accuracy as a designed ceiling**, never as production accuracy
