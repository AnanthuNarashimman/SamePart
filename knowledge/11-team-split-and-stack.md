# Team split, tech stack, and the working agreement

We are speed-running. This file exists so that two people can build in parallel without
waiting on each other, and without discovering on day three that the shapes do not match.

**The single rule that makes parallel work possible:** the API contract in section 4 is
agreed once, early, and then frozen. Backend builds behind it. Frontend builds against it.
Neither waits for the other. Changes to it happen by agreement, not unilaterally.

---

## 1. Who owns what

| Owner | Area | Ships |
|---|---|---|
| **Aditya** | Backend | Ingestion, extraction, retrieval, the matching cascade, conflict gates, canonical registry, review API, analytics queries |
| **Ananthu** | Frontend | The five pages in [10-frontend-plan.md](10-frontend-plan.md), API integration, the demo walkthrough |

### The other four seats

SIH teams are **exactly six**, at least one female member
([01](01-sih-2026-format-and-timeline.md)). Two roles are locked above. The remaining four
matter and should not default to "helping with backend."

| Role | Why it is a real job |
|---|---|
| **Data and domain** | Owns the family dictionaries and the conflict-gate table. This is the shared contract the whole pipeline reads, and it is domain judgment, not code. Also owns the synthetic dataset |
| **ML and evaluation** | Owns the numbers we put on a slide: precision, recall, coverage against risk, the taxonomy classifier. Without this person we have a demo and no evidence |
| **Deck and narrative** | Owns the six-slide PDF due around 20 September, the judge Q&A drill in [03](03-gaps-and-judge-questions.md), and the demo script. This is not a spare job. Impact and clarity are 30% of the score |
| **Integration and demo reliability** | Owns the seed data, the offline demo path, the export, and making sure the thing runs on the day |

---

## 2. Tech stack

### Backend
| Layer | Choice | Note |
|---|---|---|
| Language | **Python 3.12** | macOS ships 3.9, which pydantic v2 cannot use. Install 3.12 before anything else |
| API | **FastAPI** | Auto-generates OpenAPI, which is how the frontend gets free types |
| ORM | **SQLAlchemy 2.0** | Typed, modern |
| Database | **SQLite** now, Postgres later | A connection-string swap. No Docker, no setup tax on six people |
| Validation | **Pydantic v2** | Same models serve the API and the dictionary loader |
| Retrieval | **numpy** in-memory cosine | No vector database at demo scale |
| Model access | **Azure OpenAI** via the `openai` SDK | Behind one interface, so a local open-weight model is a config change |
| Tests | **pytest** | |

### Frontend
| Layer | Choice | Note |
|---|---|---|
| Framework | **React + TypeScript + Vite** | |
| Data fetching | **TanStack Query** | Caching, loading and error states for free. Do not hand-roll fetch state |
| Types | **Generated from the backend OpenAPI schema** | Never hand-write the response types. They will drift |
| Charts | A light chart library for the dashboard | Ananthu's call |
| Styling | Ananthu's call | Pick in hour one and do not revisit |

### Shared
- **Git**: both of us are editing `knowledge/`. **Pull before you write.** We already had one
  interleaved push that only worked because of this
- **Environment**: `.env` locally, `.env.example` committed. Keys never committed

---

## 3. What already exists

Built and verified locally, not yet pushed:

- **Dictionaries as data, not code.** A unit registry with real conversions, and a hex-bolt
  family file holding attributes, criticality levels, conflict gates and substitution groups.
  Adding a family means adding a file
- **Unit engine.** Normalises to base units and computes comparable per-unit prices
- **Conflict-gate engine.** Verified on six cases, including the one where identity evidence
  contradicts a critical conflict and the system correctly refuses in both directions
- **Database schema.** Nine tables, additive by design, decisions append-only
- **Synthetic generator.** 654 records across four simulated CPSEs, each writing in its own
  house style, with manufacturer part numbers on about half, varied units of issue, and
  price variance. Ground truth in a separate labels file. Five demo cases seeded deliberately

Table and verdict names match [10-frontend-plan.md](10-frontend-plan.md): `candidate_match`,
`approved_mapping`, `known_conflict`, `possible_alternative`, and verdicts `same_material`,
`possible_alternative`, `different`, `insufficient_evidence`.

---

## 4. The API contract

**Freeze this first. Everything else depends on it.**

Base path `/api`. FastAPI publishes the live schema at `/openapi.json`; generate frontend
types from it rather than writing them by hand.

### Ingestion
```
POST   /api/orgs                  { code, name }                  -> Org
GET    /api/orgs                                                  -> Org[]
POST   /api/imports               multipart: file, org_code, family, column_map
                                                                  -> { import_id, status }
GET    /api/imports/{id}          -> { status, rows_read, rows_ingested, extracted, errors[] }
```

### Review queue
```
GET    /api/queue                 ?group=&cursor=&limit=
       -> { counts: { needs_input, possible_alternative, same_material, different },
            items: QueueItem[], next_cursor }

GET    /api/matches/{id}          -> MatchDetail
POST   /api/matches/{id}/decision { action, note?, provided_attributes? }
       action = approve | reject | request_info
       -> { canonical_id?, new_state }
```

### Duplicate prevention
```
POST   /api/check                 { description, org_code, family?, uom?, quantity? }
       -> { verdict, candidates: MatchDetail[], safe_to_create: bool }
```

### Analytics
```
GET    /api/analytics/summary     -> { records, canonical_materials, merged, conflicts_caught,
                                       queue_by_group, duplicate_rate }
GET    /api/analytics/savings     -> { clusters: [ { canonical_id, description, orgs[],
                                       price_min, price_max, spread_pct, total_qty,
                                       aggregation_opportunity } ] }
```

### Families (powers the live-bootstrap demo)
```
GET    /api/families              -> [ { family, label, attribute_count, gate_count } ]
POST   /api/families              raw YAML body -> { family, loaded: true }
```

### Core shapes

`MatchDetail` is the one that matters most, because the comparison view is the whole product.

```
MatchDetail {
  id, verdict, decided_by, score?, review_state,
  gate_overrode: bool,
  gate_firings: [ { gate_id, action, message, attributes[], detail } ],
  substitution_conditions: string[],
  notes: string[],
  a: RecordView,
  b: RecordView
}

RecordView {
  record_id, org_code, source_code, raw_description,
  uom, base_uom, quantity, unit_price, unit_price_base, currency,
  standardised_short?,
  attributes: [ { key, label, value, unit, status, method, evidence, confidence } ]
}
```

`status` is one of `extracted | unknown | derived`. `method` is one of
`regex | llm | derived | given`. **The frontend renders `unknown` explicitly rather than
hiding the row.** A missing critical attribute is the reason the system is asking a
question, so it has to be visible.

`evidence` is the substring of the source description that justified the value. The
comparison view should show it under the value. This is our differentiator; do not let it
become a tooltip nobody opens.

---

## 5. How we avoid blocking each other

1. **Hour one: backend ships every endpoint above as a stub** returning realistic fixture
   JSON, with CORS on. Frontend is unblocked immediately and never waits for the pipeline
2. **Fixtures are committed** so both sides render the same five demo cases
3. **Backend replaces stubs with real logic behind the same shapes.** Frontend does not
   need to know when this happens
4. **Contract changes are a conversation, never a surprise.** If a shape has to change, say
   so before you push it

---

## 6. Build order

Aligned with the priority in [10-frontend-plan.md](10-frontend-plan.md).

| Phase | Backend (Aditya) | Frontend (Ananthu) |
|---|---|---|
| **0. Foundations** | Dictionaries, units, gates, schema, synthetic data. **Done** | Project scaffold, routing, layout, API client, generated types |
| **1. The spine** | Ingestion, extraction with evidence, retrieval, the cascade, gates, review API, canonical registry | Import page, Reconciliation Desk with the grouped queue and comparison view |
| **2. Credibility** | Calibration and auto-merge threshold, evaluation harness, taxonomy classifier, standardised descriptions | Evidence display, survivorship display on approve, unknown-state handling |
| **3. Impact** | Analytics queries, price variance, demand aggregation, check-before-create, ERP-shaped export | Dashboard, duplicate-prevention page |
| **4. Demo** | Live family bootstrap, local model swap, seeded demo path | Demo polish, offline path, optional relationship graph |

Phases 0 and 1 are "something real that works." **Phase 3 is what the judges remember**, so
do not let it slip to last.

---

## 7. Setup checklist

**Both**
- [ ] Python 3.12 installed (`python3.12 -V`). The system 3.9 will not work
- [ ] Node 20+ installed
- [ ] Repo cloned, `pull` before every writing session

**Aditya, backend**
- [ ] Virtual environment on 3.12, dependencies installed
- [ ] `.env` filled from `.env.example`
- [ ] **Azure OpenAI details needed before anything can call a model:** endpoint URL, API
      key, API version, chat deployment name, embedding deployment name
- [ ] Stub endpoints live with CORS on, within the first session

**Ananthu, frontend**
- [ ] Vite app scaffolded, types generated from `/openapi.json`
- [ ] Styling and chart library chosen and not revisited

---

## 8. Definition of done for the demo

The demo works when all five of these run end to end without manual intervention:

1. Import three simulated catalogues
2. Two records worded completely differently are proposed as a match, approved, and **both
   source codes are visibly retained**
3. A record with one conflicting critical attribute is **refused**, with the exact conflict
   named
4. An incomplete record makes the system **ask** for the missing attribute, receive it, and
   update its recommendation
5. Check-before-create surfaces an existing match before a new code is minted

Then the dashboard shows a rupee number, and a new material family is added live.

---

## 9. Things that will bite us if we ignore them now

- **The deck is due before the software.** Around 20 September, six slides, PDF. Somebody
  owns it from day one, not the night before
- **No live network calls in the demo path.** It will fail at the worst moment
- **Label simulated data as simulated**, on the slide, before a judge asks
- **Units before money.** Price comparison is invalid until units are normalised
- **Do not blend accuracy numbers.** Benchmark, real Indian text, and synthetic are three
  separate claims with three separate limits ([07](07-datasets.md))
