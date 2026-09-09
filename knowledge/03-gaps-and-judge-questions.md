# Gaps, and the questions we cannot yet answer

## Seven gaps, in order of how much they cost us

### 1. Nothing in the system can decide without a human — architecture
The plan rules out calibrated confidence scores because an uncalibrated number misleads.
The principle is right and the conclusion is wrong. No score means no threshold, no
auto-merge, and a person on every candidate pair in a multi-million-record master.

**Fix:** keep the four-way label as what we show. Drive it from a calibrated score
underneath. Report coverage against risk, meaning the share of pairs decided automatically
at a held precision. That single curve answers accuracy, scale and trust at once.

### 2. No answer to "how does this run for twenty CPSEs" — scale
A model call per candidate pair does not survive three million line items. We have
embedding retrieval, which is blocking, but we never state the cascade, the surviving pair
count, the share that reaches a model, or a cost.

**Fix:** state the cascade explicitly — deterministic identity, then blocking, then a cheap
local classifier, then a model only on the ambiguous band — and do the arithmetic on one
slide.

### 3. Material master data leaving the network — sovereignty
Our default matching path calls an external API. A public sector audience will ask where
their data goes. This is the likeliest single point of failure in the room.

**Fix:** an open-weight model inside the CPSE's own environment, hosted API for the
prototype only. The evidence supports us here: on a 755,540-pair expert-labelled benchmark,
a rule baseline scores 91.3 F1, GPT-4o scores 99.0, and a distilled 14B **open** model
scores 98.2. Losing under a point to keep data on premises is an easy argument to win.

### 4. No manufacturer, no part number — data model
Manufacturer plus manufacturer part number is the highest-precision identity signal in real
material masters, and SAP already models many-codes-to-one-item exactly this way through
separate manufacturer-part records linked to one inventory material.

**Fix:** add both fields. They give a deterministic high-confidence rule that needs no model
call, and they make the equivalence case interesting, because two makers' interchangeable
parts are exactly the "possible alternative" verdict.

### 5. A hundred and fifty records cannot support an accuracy claim — evidence
At that size, precision and recall are noise, and an informed judge will say so. Synthetic
data is free; there is no reason for the set to be small.

### 6. One material family, no generalisation story — scope
Hex bolts only is the correct build decision and an unprepared answer. "Does this work for
valves, pumps, cables, instrumentation" is certain to be asked.

**Fix:** do not hardcode a second family. Keep schema and gates as **data**, then add a
family live in front of the judges. The weakness becomes the strongest moment in the demo.

### 7. No money anywhere in the document — impact
The PS Expected Impact section is almost entirely economic. We quantify none of it, and
impact is a fifth of the score.

**Fix:** add price, quantity and unit to records. Once clusters exist, aggregation and
price-variance views are a grouping query, and they produce the only number a judge will
still remember an hour later.

---

## The judge Q&A drill

Fourteen questions a CPCL or ministry evaluator will plausibly ask, and whether we can
answer them today.

| Question | Status |
|---|---|
| "How long does this take on three million line items, and what does it cost?" | **No answer** |
| "Does our material master data leave our network?" | **No answer** |
| "Same bolt, one stocks it in numbers, one in boxes of a hundred, one by weight." | **No answer** |
| "How much money does this save?" | **No answer** |
| "How is this different from SAP's own governance module, or the Indian vendors already selling this?" | **No answer** |
| "You did bolts. Our master is valves, pumps, cables, chemicals." | **No answer** |
| "When five records merge, whose description and whose specification wins?" | **No answer** (no survivorship rules) |
| "Can one CPSE see another's vendors and prices?" | **No answer** (no tenancy boundary) |
| "Where is the machine learning? This looks like prompting." | **Weak** |
| "What is the national code actually made of? Show me one." | **Weak** |
| "Who decides that another CPSE's code and ours are the same material?" | **Partial** (one undifferentiated reviewer, no dispute path) |
| "We are never changing our SAP codes." | **Answered.** Additive canonical ID with full back-mapping. Lead with this. |
| "What happens when it is wrong and the wrong part goes into a unit?" | **Answered.** Our strongest area. Say plainly that a wrong merge in a refinery is a safety incident, not a data problem. |
| "Once it is clean, how does it stay clean?" | **Answered.** Check-before-create. It is currently fifth of six in our demo script and should be promoted. |
