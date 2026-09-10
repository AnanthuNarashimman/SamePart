# Deployment decision: where the model runs

Settled 10 September 2026. This is the answer to "does our material master data leave our
network", which is the question most likely to end a pitch in front of a public sector
audience.

## The decision

**Weights are downloaded. Inference is in-house.**

An open-weight model is pulled once from a public model registry, placed on infrastructure
the CPSE controls, and served from there. After that the system runs with no dependency on
any external service.

That distinction is the whole thing, and it is easy to get wrong:

| | Weights from a registry | Model hosted by a third party |
|---|---|---|
| What crosses the network | a file, once | **every material description, forever** |
| Sovereign | yes | **no** |
| Works air-gapped | yes | no |

A Qwen model called through a hosted inference endpoint is **not** sovereignty. It swaps one
external endpoint for another and leaves the original objection exactly where it was. Getting
this wrong in a pitch is worse than not raising it, because a refinery IT reviewer will make
the distinction for you.

## The three states, and which one ships

| | Model | Data leaves | Use |
|---|---|---|---|
| **Deterministic only** | none | never | the default. Handles 93.5% of decisions |
| **Prototype** | hosted, Azure | specifications only, when explicitly enabled | demonstrations |
| **Production** | open-weight, CPSE infrastructure | never | deployment |

The first is what the system does with no configuration at all. Egress is blocked by default;
enabling it is a deliberate act, and every attempt is recorded with its exact payload whether
it goes or not.

## What is already built

This is a "we will do it later" claim with unusually little left to do.

- A local model client speaking the OpenAI-compatible endpoint that Ollama, vLLM,
  llama.cpp and LM Studio all expose. It never touches the egress guard, because nothing
  leaves the host
- `get_model()` **prefers the local model** whenever one is configured and reachable,
  regardless of what else is available. The hosted path is the fallback, not the default
- Switching is two environment variables
- `/api/health` reports `runs_on_host` and `data_leaves_network` as fields, so the answer is
  observable rather than argued

**Not yet done: the weights have never been run.** Say so if asked. See "What not to claim".

## Practical numbers, so it is a plan rather than a slogan

**Sizing.** Roughly 6GB of GPU memory for a 7B model at 4-bit, 10 to 12GB for a 14B. One
mid-range inference card. Not a datacentre.

**Throughput.** Only 6.5% of candidate pairs reach the model at all, and the initial
harmonisation is a one-time pass. Steady state is new material requests, a handful per CPSE
per month. The system is not sized for continuous load.

**Air-gapped operation.** Weights are moved in once; the system then runs with no internet
connection. For a refinery network this is the requirement, not a compromise.

**Licence.** Check the specific variant chosen. Open-weight families differ by size: some are
Apache 2.0 and freely usable commercially, others carry their own terms. "Is it actually free
for a government deployment" is a fair question and "I think so" is a bad answer.

## The evidence that the quality cost is small

On a 755,540-pair expert-labelled benchmark:

| Matcher | F1 |
|---|---|
| Rule-based baseline | 91.3 |
| GPT-4o | 99.0 |
| **Distilled 14B open model** | **98.2** |

Under a point of F1 to keep data in the building. Also worth knowing: there is published work
on models instruction-tuned specifically for data preprocessing tasks including entity
matching, at 7B and 13B, reporting parity with hosted frontier models on this task class.
That is a better-aimed choice than a general instruct model, and it gives the slide a
citation instead of a preference.

## What to say

> The deterministic core handles 93.5% of decisions on-premises with no model at all. For the
> remaining ambiguous band this prototype calls a hosted model, and we can show you exactly
> what it sends: specifications only, no material codes, no organisation names, no prices or
> vendors. Production pulls an open-weight model onto the CPSE's own servers and runs
> air-gapped. The client for that is built, and the default posture is already blocked.

## What not to claim

**Do not imply the open-weight path has been benchmarked.** It has not been run. The client
exists, the configuration exists, the weights were never downloaded.

If asked directly whether you have run it: say no, then say the client is built and
config-driven, and point at the published benchmark as the reason you expect the result to
hold. That is evidence rather than assertion, and it costs nothing.

Implying otherwise and then being asked for numbers loses more credibility than the point was
worth.
