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
