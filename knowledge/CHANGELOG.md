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

## 2026-09-09

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
