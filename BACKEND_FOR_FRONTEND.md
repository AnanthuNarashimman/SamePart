# Backend status, for whoever builds the UI

Written for the frontend and for any coding agent working on it. Everything below is a real
response captured from the running API, not an illustration.

**Start here:** [`knowledge/00-start-here.md`](knowledge/00-start-here.md) for what the
project is. [`knowledge/10-frontend-plan.md`](knowledge/10-frontend-plan.md) for what the
pages should do. [`knowledge/CHANGELOG.md`](knowledge/CHANGELOG.md) before changing anything.

---

## Run it

```bash
python3.12 -m venv .venv                      # 3.12 required; macOS system 3.9 will not work
./.venv/bin/pip install -r requirements.txt
PYTHONPATH=backend SAMEPART_MODE=live ./.venv/bin/python -m samepart.cli seed
PYTHONPATH=backend SAMEPART_MODE=live ./.venv/bin/uvicorn samepart.api.app:app --reload --port 8000
```

`seed` builds the database, generates four simulated CPSE catalogues plus four years of
purchase orders, extracts attributes, runs matching, and auto-merges what is unambiguous.
It takes under a minute and is deterministic, so everyone gets identical data.

Generate types from the live schema rather than writing them by hand:

```bash
npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/types.ts
```

Cross-origin requests are open in development. Interactive docs at `/docs`.

## What is real and what is still fixtures

`SAMEPART_MODE=live` uses the database. `stub` returns fixtures **in exactly the same
shapes**, so you can build against either. `GET /api/health` reports which are live.

| Service | Endpoints | Status |
|---|---|---|
| catalogue | `/orgs`, `/imports` | **live** |
| review | `/queue`, `/matches/*`, decisions | **live** |
| questions | `/questions`, `/records/*/answer`, `/unresolvable` | **live** |
| analytics | `/analytics/*` | **live** |
| prevention | `/check` | stub |
| families | `/families` | stub |

A stubbed endpoint will not change shape when it goes live. Build against it now.

## Endpoints

```
GET   /api/health
GET   /api/orgs                            POST /api/orgs
POST  /api/imports                         GET  /api/imports/{import_id}
GET   /api/queue                           GET  /api/matches/{match_id}
POST  /api/matches/{match_id}/decision
GET   /api/questions
POST  /api/records/{record_id}/answer
POST  /api/records/{record_id}/unresolvable
GET   /api/analytics/summary               GET  /api/analytics/savings
GET   /api/analytics/rationalisation       GET  /api/analytics/audit-flags
POST  /api/check
GET   /api/families                        POST /api/families
```

---

## The dashboard

### `GET /api/analytics/summary`

```json
{
  "records": 654,
  "canonical_materials": 181,
  "merged": 471,
  "conflicts_caught": 0,
  "duplicate_rate": 0.4434,
  "queue_by_group": {
    "needs_input": 689,
    "possible_alternative": 438,
    "same_material": 20,
    "different": 1893
  },
  "procurement_lines": 1418,
  "total_spend": 290431971.12,
  "spend_window": "last 4 financial years",
  "dead_codes": 124,
  "dead_code_rate": 0.1896,
  "shared_materials": 180,
  "currency": "INR",
  "by_org": [
    {
      "org_code": "BPCL",
      "records": 168,
      "mapped_to_canonical": 127,
      "duplicate_rate": 0.756,
      "dead_codes": 26
    },
    {
      "org_code": "CPCL",
      "records": 159,
      "mapped_to_canonical": 111,
      "duplicate_rate": 0.6981,
      "dead_codes": 24
    },
    {
      "org_code": "IOCL",
      "records": 160,
      "mapped_to_canonical": 113,
      "duplicate_rate": 0.7063,
      "dead_codes": 40
    },
    {
      "org_code": "NTPC",
      "records": 167,
      "mapped_to_canonical": 120,
      "duplicate_rate": 0.7186,
      "dead_codes": 34
    }
  ]
}
```

`duplicate_rate` is high because the generated data is deliberately duplicate-heavy. Do not
label it as a real-world rate on screen.

### `GET /api/analytics/savings`

```json
{
  "currency": "INR",
  "total_opportunity": 39129135.58,
  "total_spend": 202953973.04,
  "shared_materials": 136,
  "window": "last 4 financial years",
  "excluded_flagged_clusters": 6,
  "excluded_opportunity": 7858979.75,
  "clusters": [
    {
      "canonical_id": "SMP-000002",
      "standardised_short": "BOLT, HEX HEAD; M10X120; A2-70; DIN931",
      "orgs": [
        "BPCL",
        "CPCL",
        "IOCL",
        "NTPC"
      ],
      "price_min": 111.33,
      "price_max": 177.68,
      "spread_pct": 59.6,
      "total_quantity": 108787.0,
      "total_spend": 15605143.07,
      "po_lines": 13,
      "aggregation_opportunity": 3493886.36
    },
    {
      "canonical_id": "SMP-000139",
      "standardised_short": "BOLT, HEX HEAD; M6X35; A4-70; ISO4014",
      "orgs": [
        "CPCL",
        "NTPC"
      ],
      "price_min": 136.18,
      "price_max": 192.58,
      "spread_pct": 41.4,
      "total_quantity": 50175.0,
      "total_spend": 9015786.0,
      "po_lines": 6,
      "aggregation_opportunity": 2182954.5
    }
  ]
}
```

**Two fields matter for honesty and should be visible on the page, not hidden.**
`excluded_flagged_clusters` and `excluded_opportunity` are money we deliberately do **not**
claim, because those merges are under audit and may be wrong. Showing the withheld figure
next to the claimed one is the point, not a footnote.

### `GET /api/analytics/rationalisation`

Capability 5. Codes nobody has ordered in four years.

```json
{
  "window": "last 4 financial years",
  "records": 654,
  "dead_codes": 124,
  "dead_code_rate": 0.1896,
  "duplicate_codes_removable": 290,
  "items": [
    {
      "record_id": 325,
      "org_code": "BPCL",
      "source_code": "BPCL-000006",
      "raw_description": "BLT HEX HD M20X60MM  A2-70  ISO 4017",
      "canonical_id": "SMP-000032",
      "last_purchase": null
    },
    {
      "record_id": 330,
      "org_code": "BPCL",
      "source_code": "BPCL-000011",
      "raw_description": "BLT HEX HD M8X60MM  GR 10.9  ISO 4017  GALVANISED",
      "canonical_id": "SMP-000030",
      "last_purchase": null
    }
  ]
}
```

### `GET /api/analytics/audit-flags`

Merges the system nominates for a second look, using spend patterns that played no part in
making the merge. Measured at 100% precision and 50% recall on the generated data, so
present it as **a screening tool, not a proof**. A flagged cluster is worth a look; an
unflagged one is not proven correct.

```json
{
  "median_spread_all": 1.429,
  "threshold": 2.143,
  "flagged": 6,
  "items": [
    {
      "canonical_id": "SMP-000004",
      "standardised_short": "BOLT, HEX HEAD; M8X60; 10.9; ISO4017",
      "reason": "Unit price varies 32.9x across buyers, against a median of 1.4x. Spend data played no part in this merge, so the pattern is independent evidence it may be wrong.",
      "price_spread": 32.86,
      "orgs": [
        "BPCL",
        "NTPC"
      ],
      "source_codes": [
        "BPCL-000015",
        "BPCL-000052",
        "NTPC-000015"
      ]
    },
    {
      "canonical_id": "SMP-000023",
      "standardised_short": "BOLT, HEX HEAD; M10X80; A2-70; DIN931",
      "reason": "Unit price varies 7.9x across buyers, against a median of 1.4x. Spend data played no part in this merge, so the pattern is independent evidence it may be wrong.",
      "price_spread": 7.85,
      "orgs": [
        "BPCL",
        "IOCL",
        "NTPC"
      ],
      "source_codes": [
        "BPCL-000030",
        "IOCL-000022",
        "IOCL-000025",
        "NTPC-000034"
      ]
    }
  ]
}
```

---

## The reconciliation desk

### `GET /api/queue`

```json
{
  "counts": {
    "needs_input": 689,
    "possible_alternative": 438,
    "same_material": 20,
    "different": 1893
  },
  "items": [
    {
      "id": 3,
      "verdict": "insufficient_evidence",
      "review_state": "queued",
      "a_description": "Bolt, Hexagon Head, M8 x 16mm  Property Class CLASS 10.9  Conforming to DIN 933  Zp",
      "b_description": "Bolt, Hexagon Head, M8 x 16mm  Conforming to DIN 933  Zinc Plated",
      "a_org": "IOCL",
      "b_org": "IOCL",
      "headline": "Cannot decide safely: unknown on at least one record: grade"
    },
    {
      "id": 2,
      "verdict": "different",
      "review_state": "queued",
      "a_description": "BOLT HEX HEAD; DIA 6MM; LG 70MM  GRADE SS316 A4-70  ISO4014  HOT DIP GALVANISED",
      "b_description": "BOLT HEX HEAD; DIA 6MM; LG 70MM  GRADE GR 8.8  DIN 931  BLACK",
      "a_org": "NTPC",
      "b_org": "NTPC",
      "headline": "Different material: grade: A4-70 vs 8.8; finish: HOTDIPGALVANISED vs PLAIN"
    }
  ],
  "next_cursor": "2"
}
```

Group in this order, which is reviewer priority rather than alphabetical:
`needs_input`, `possible_alternative`, `same_material`, `different`. Collapse `different` by
default; it needs no action.

### `GET /api/matches/{id}`

Attribute lists are truncated here for length; the real response carries all ten.

```json
{
  "id": 2,
  "verdict": "different",
  "decided_by": "attributes",
  "score": 0.6308,
  "review_state": "queued",
  "gate_overrode": false,
  "gate_firings": [
    {
      "gate_id": "critical_conflict",
      "action": "force_different",
      "message": "A critical attribute differs. These are not the same material.",
      "attributes": [
        "grade",
        "finish"
      ],
      "detail": "grade: A4-70 vs 8.8; finish: HOTDIPGALVANISED vs PLAIN"
    }
  ],
  "substitution_conditions": [],
  "notes": [
    "2 of 7 comparable attributes disagree."
  ],
  "a": {
    "record_id": 580,
    "org_code": "NTPC",
    "source_code": "NTPC-000093",
    "raw_description": "BOLT HEX HEAD; DIA 6MM; LG 70MM  GRADE SS316 A4-70  ISO4014  HOT DIP GALVANISED",
    "standardised_short": "BOLT, HEX HEAD; M6X70; A4-70; ISO4014",
    "uom": "EA",
    "base_uom": "EA",
    "quantity": 25.0,
    "unit_price": 20.66,
    "unit_price_base": 20.66,
    "currency": "INR",
    "attributes": [
      {
        "key": "manufacturer",
        "label": "Manufacturer",
        "value": null,
        "unit": null,
        "status": "unknown",
        "method": "regex",
        "evidence": null,
        "confidence": null,
        "criticality": "identity"
      },
      {
        "key": "manufacturer_part_number",
        "label": "Manufacturer part number",
        "value": null,
        "unit": null,
        "status": "unknown",
        "method": "regex",
        "evidence": null,
        "confidence": null,
        "criticality": "identity"
      },
      {
        "key": "thread_diameter_mm",
        "label": "Nominal thread diameter",
        "value": 6.0,
        "unit": "mm",
        "status": "extracted",
        "method": "regex",
        "evidence": "DIA 6MM",
        "confidence": 0.99,
        "criticality": "critical"
      },
      {
        "key": "thread_pitch_mm",
        "label": "Thread pitch",
        "value": null,
        "unit": null,
        "status": "unknown",
        "method": "regex",
        "evidence": null,
        "confidence": null,
        "criticality": "major"
      }
    ]
  },
  "b": {
    "record_id": 627,
    "org_code": "NTPC",
    "source_code": "NTPC-000140",
    "raw_description": "BOLT HEX HEAD; DIA 6MM; LG 70MM  GRADE GR 8.8  DIN 931  BLACK",
    "standardised_short": "BOLT, HEX HEAD; M6X70; 8.8; DIN931",
    "uom": "EA",
    "base_uom": "EA",
    "quantity": 10.0,
    "unit_price": 11.84,
    "unit_price_base": 11.84,
    "currency": "INR",
    "attributes": [
      {
        "key": "manufacturer",
        "label": "Manufacturer",
        "value": null,
        "unit": null,
        "status": "unknown",
        "method": "regex",
        "evidence": null,
        "confidence": null,
        "criticality": "identity"
      },
      {
        "key": "manufacturer_part_number",
        "label": "Manufacturer part number",
        "value": null,
        "unit": null,
        "status": "unknown",
        "method": "regex",
        "evidence": null,
        "confidence": null,
        "criticality": "identity"
      }
    ]
  }
}
```

**Three things the comparison view must do.**

1. **Render `status: "unknown"` rows explicitly.** Do not hide them. A missing critical
   attribute is the reason the system is asking a question
2. **Show `evidence` under each value.** It is the substring of the source description that
   proved that value, and it is the whole differentiator. Do not bury it in a tooltip
3. **Show `gate_firings` and `substitution_conditions`.** When a merge is refused, the exact
   conflict is named. When a substitute is proposed, the condition under which it is safe is
   attached, and a person needs to read it

`POST /api/matches/{id}/decision` takes `{"action": "approve" | "reject" | "request_info"}`.
Approving an `insufficient_evidence` pair is refused with a 500 and a message; the UI should
offer "answer the question" there instead of "approve".

---

## The question view, which is where the volume is

`GET /api/questions`

```json
{
  "pairs_deferred": 689,
  "questions": 228,
  "records": 207,
  "curve": [
    {
      "questions_answered": 10,
      "pairs_cleared": 130,
      "share_cleared": 0.1887
    },
    {
      "questions_answered": 25,
      "pairs_cleared": 221,
      "share_cleared": 0.3208
    },
    {
      "questions_answered": 50,
      "pairs_cleared": 348,
      "share_cleared": 0.5051
    },
    {
      "questions_answered": 100,
      "pairs_cleared": 508,
      "share_cleared": 0.7373
    },
    {
      "questions_answered": 200,
      "pairs_cleared": 656,
      "share_cleared": 0.9521
    },
    {
      "questions_answered": 228,
      "pairs_cleared": 675,
      "share_cleared": 0.9797
    }
  ],
  "items": [
    {
      "record_id": 148,
      "org_code": "CPCL",
      "source_code": "CPCL-000148",
      "raw_description": "HEX BOLT M16X50  ISO 4014",
      "missing": [
        {
          "key": "grade",
          "label": "Property class or grade",
          "criticality": "critical",
          "pairs_blocked": 20,
          "counterpart_values": [
            {
              "value": "10.9",
              "seen_on": 7
            },
            {
              "value": "8.8",
              "seen_on": 7
            },
            {
              "value": "A2-70",
              "seen_on": 3
            },
            {
              "value": "A4-70",
              "seen_on": 2
            }
          ]
        },
        {
          "key": "finish",
          "label": "Surface finish",
          "criticality": "critical",
          "pairs_blocked": 17,
          "counterpart_values": [
            {
              "value": "PLAIN",
              "seen_on": 8
            },
            {
              "value": "PASSIVATED",
              "seen_on": 3
            },
            {
              "value": "ZINCPLATED",
              "seen_on": 3
            },
            {
              "value": "HOTDIPGALVANISED",
              "seen_on": 3
            }
          ]
        }
      ],
      "pairs_blocked": 20
    }
  ],
  "next_cursor": "2"
}
```

**Read this before designing the screen.** The queue holds 689 deferred pairs, but that is
not 689 reviews. The same record appears in many blocked pairs and one answer clears all of
them:

| | |
|---|---|
| Deferred pairs | 689 |
| Distinct blanks | 228 |
| **Records a person opens** | **207** |

So the screen is **one card per record**, not one row per pair. Each card shows the blanks,
what counterpart records say for that field, and how many pairs the answer unblocks.

`curve` is the diminishing-returns curve. Ten answers clear 19% of the queue, fifty clear
51%, a hundred clear 74%. **Show it.** It exists so a data owner stops early on purpose
rather than feeling obliged to empty a queue.

Two actions per card:

- `POST /api/records/{id}/answer` with `{"values": {"grade": "8.8"}}`
- `POST /api/records/{id}/unresolvable` with `{"keys": ["grade"], "reason": "..."}`
  for when the answer does not exist anywhere. This is what stops a queue being permanent

---

## Import: errors are not warnings

`ImportStatus` has three separate fields and they mean different things.

- `errors` — things that went **wrong**. Empty list means the import succeeded
- `warnings` — not failures. Rows skipped because they were already imported land here
- `rows_skipped` — a count

**Render warnings differently from errors.** Re-importing a file is safe and skips
everything, which is correct behaviour, not a failure. Showing that as an error makes a
working import look broken.

**Import triggers matching automatically.** No manual step. The response carries what the
upload actually did, so show it: `candidate_pairs`, `auto_merged`, `queued_for_review`.
Uploading 19 rows returns in about 165 ms and the queue reflects it immediately.

Sample file to try: `samples/HPCL_sample_upload.csv`, upload as org `HPCL`, family
`hex_bolt`.

## Things that will bite you

- **`unit_price` and `unit_price_base` are different numbers.** One box of a hundred costs
  4,180 and each costs 41.80. Always display and compare `*_base`. Getting this wrong
  produces a hundredfold error in a figure someone reads off a slide
- **Verdict values are** `same_material`, `possible_alternative`, `different`,
  `insufficient_evidence`. Not `same`
- **`review_state`** can be `queued`, `approved`, `rejected`, `info_requested`, or
  `auto_approved`. Auto-approved pairs were merged by rule with nobody asked, and 1 in 20 is
  routed back for audit
- **Money is INR.** Format in lakh and crore, not thousands
- **Label simulated data as simulated on screen.** Organisation names carry "(simulated)"
  already; keep it visible

## Not built yet, do not design around it

Classification into a taxonomy, the model tier, ERP export, and governance roles. The
ordered plan is in [`knowledge/13-ps-anchored-plan.md`](knowledge/13-ps-anchored-plan.md).
