# SamePart

Cross-organisation material identity resolution for **SIH26099**, AI-Driven Standardization
and Harmonization of Material Codes Across CPSEs.

The same bolt appears on four CPSEs' material masters under four different codes and four
different descriptions. SamePart works out which entries are secretly the same part, gives
each one a national code, and **never touches anyone's existing code**.

**Building the UI?** Read [`BACKEND_FOR_FRONTEND.md`](BACKEND_FOR_FRONTEND.md) — every
endpoint with real captured responses, what is live, and what will bite you.

Start with [`knowledge/00-start-here.md`](knowledge/00-start-here.md).
Before changing anything, read [`knowledge/CHANGELOG.md`](knowledge/CHANGELOG.md).

## Quick start, backend

Requires **Python 3.12**. The system Python on macOS is 3.9 and will not work.

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in Azure values; not needed for stub mode
PYTHONPATH=backend ./.venv/bin/uvicorn samepart.api.app:app --reload --port 8000
```

That starts in **stub mode**, which is what you want while building the UI. To run against
the real pipeline — and for anything you are going to show someone — see
[Demo day](#demo-day) below, because the mode is silent and easy to get wrong.

- Interactive docs: http://127.0.0.1:8000/docs
- Machine-readable schema: http://127.0.0.1:8000/openapi.json
- Health and current mode: http://127.0.0.1:8000/api/health

## Quick start, frontend

The API runs in **stub mode** by default. Every endpoint returns realistic fixture data in
exactly the shape the live implementation will return, so **the frontend is never blocked
on the pipeline**. Build against it now; the backend swaps stubs for real logic one endpoint
at a time and nothing on your side changes.

Generate types from the running server rather than hand-writing them:

```bash
npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/types.ts
```

Cross-origin requests are open in development, so any Vite port works.

The stub data is the five seeded demo cases, so what you build against is what gets
demonstrated: a clean merge, a grade conflict, an incomplete record, a conditional
substitute, and duplicate prevention.

## Demo day

Run these from the **repository root**, in this order.

```bash
cd /path/to/sih-2026                          # every path below is relative to the root
export PYTHONPATH=backend SAMEPART_MODE=live SAMEPART_MODEL_MATCHING=1
./.venv/bin/python -m samepart.cli seed       # builds the catalogues and runs the cascade
./.venv/bin/python -m samepart.cli baseline   # works the queue, creating canonical materials
./.venv/bin/uvicorn samepart.api.app:app --port 8000 &
cd frontend && npm run dev                    # proxies /api to :8000
```

**`baseline` is not optional.** `seed` leaves the database with candidate pairs and no
approved merges, so `canonical_materials` is 0, the relationship graph is empty, and the
consolidation figures read zero. `baseline` plays a reviewer working the queue and is what
gives the demo a populated starting point.

`SAMEPART_MODEL_MATCHING=1` puts the language-model tier in the cascade. Without it every
pair is settled deterministically, which sounds better than it is: the cascade chart reads
100% with an empty model slice, and the point of the chart is that the cheap tiers carry
94.5% and the model carries the 5.5% they cannot. It costs about two seconds a pair over
roughly 176 pairs, so budget five to ten minutes for the two commands together.

Then check the API is actually live before anyone is watching:

```bash
curl -s localhost:8000/api/health | python3 -m json.tool | head -14
```

`"mode": "live"` and eight entries under `live_services`. If it says `"mode": "stub"` and
`"live_services": []`, stop and fix it — see below.

### Three ways this goes wrong silently

**Forgetting `SAMEPART_MODE=live`.** It defaults to `stub`, so every endpoint returns
fixtures. Nothing errors and nothing warns: the pages render, the charts draw, the numbers
are plausible. This was deliberate — it is what let the frontend be built before the
pipeline existed — but it means a demo can run start to finish on fixture data without
anyone noticing. `/api/health` is the only reliable tell, which is why it is the first
thing to check.

**Starting the server from `backend/`.** The database path is relative, so `cd backend &&
uvicorn ...` creates a second, empty `backend/samepart.db` beside the real
`./samepart.db` and every request 500s with `no such table: candidate_match`. Run from the
root; if you already made the empty one, delete it.

**Re-running `seed` on its own.** It drops and rebuilds every table, so on its own it
*removes* the approved merges that `baseline` created. The pages still load and the charts
still draw — they just quietly report no canonical materials and an empty graph. If you run
`seed`, run `baseline` after it, every time. There are no flags to guard you here: the CLI
ignores extra arguments, so even `seed --help` rebuilds the database.

### Recognising stub mode mid-demo

The fixtures are the five seeded demo cases, so the shapes look right. The quickest visual
tell is the questions queue: stub always reports **228 blanks across 207 records**. Live
reports whatever the last seed produced — around 165 blanks across 152 records. If you see
exactly 228 and 207, you are on fixtures.


## Layout

```
backend/samepart/
  api/            HTTP layer only
    schemas.py      the contract; frontend types are generated from this
    deps.py         picks stub or live implementation per service
    routers/        one small router per concern
  services/       swappable implementations behind protocols
  dictionary/     loads the YAML families; nothing here knows what a bolt is
  pipeline/       extraction, retrieval
  db/             SQLAlchemy models
  synth/          synthetic multi-CPSE catalogue generator
dictionaries/     families, units, gates, blocking. DATA, not code
knowledge/        research, decisions, and the change log
```

## Generating the demo data

```bash
PYTHONPATH=backend ./.venv/bin/python -c \
  "from pathlib import Path; from samepart.synth.generate import generate; \
   print(generate(Path('data/generated')))"
```

Deterministic from a fixed seed, so everyone gets the same catalogue. Ground truth is
written to a separate labels file, so the pipeline cannot read the answer.

## Design rules that are not up for casual reversal

1. Families, attributes, units, gates and blocking are **data, not code**
2. Conflict gates sit **outside** the model and can veto it
3. Source codes are **never overwritten**; a canonical identity is an additional row
4. Decisions are **append-only**
5. Canonical IDs come from a registry, **never from a language model**
6. Extraction may output `unknown`; a missing critical attribute is why the system asks
7. Retrieval **proposes**, it never decides

See [`knowledge/CHANGELOG.md`](knowledge/CHANGELOG.md) for what has already been tried and
reversed, with the measurements that forced each change.
