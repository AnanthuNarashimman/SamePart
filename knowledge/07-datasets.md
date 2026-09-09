# What real data we can actually get

Two independent research passes were run on this question and **they disagreed**. The
second pass concluded no ground-truth dataset was obtainable. The first pass found one and
retrieved it. This file reflects the corrected, merged position.

## The headline: real ground truth exists, from exactly one source

**US Defense Logistics Agency FLIS / PUB LOG data.** This is the only public dataset found
that carries genuine "one item, many codes" ground-truth labels.

| File | Contents | Rows |
|---|---|---|
| `REFERENCE.zip` → `V_FLIS_PART.CSV` | `NIIN, PART_NUMBER, CAGE_CODE, CAGE_STATUS, RNCC, RNVC` | **16,442,614** |
| `IDENTIFICATION.zip` → `P_FLIS_NSN.CSV` | Item name and nomenclature per NSN | 16.9M |
| `IDENTIFICATION.zip` → `V_FLIS_STANDARDIZATION.CSV` | **Explicit NIIN-to-NIIN equivalence relations** | **378,572** |
| `IDENTIFICATION.zip` → `V_COLLOQUIAL_NAME.CSV` | Synonym data | — |
| `CAGE.zip` → `P_CAGE.CSV` | CAGE code → real company name and location | 4M |

Roughly **7.2M unique NIINs**, some with over 1,000 cross-referenced part numbers from
different manufacturers. That is precisely the structure our system claims to reconstruct:
one canonical identity, many organisational codes.

The standardization table is a **second, independent ground-truth signal** — explicit
item-to-item equivalence, which maps onto our "possible alternative" verdict.

**Status and caveats:**
- Format is plain CSV, cleanly extractable
- Licence is effectively public-domain US government / FOIA data; DLA's own FAQ states
  PUB LOG non-restricted data is free and intended for public reuse
- `dla.mil` currently returns **HTTP 403 to automated fetchers** (bot/WAF block). A human
  with a browser very likely succeeds. Verified retrieval this session was via **Wayback
  Machine mirrors captured April–May 2025**
- `CHARACTERISTICS.zip` (the MRC item-attribute data) was **not** confirmed reachable
- Domain is US military logistics, not Indian PSU procurement. Say so plainly

**Verdict: USABLE, and by a wide margin the best option for Phase 2 evaluation.**

## Confirmed working, verified live

| Source | What you get | Labels? |
|---|---|---|
| [UNSPSC via UNGM](https://www.ungm.org/Public/UNSPSC/Excel) | `.xlsx`, 13,336 rows, full 4-level hierarchy, no login | Taxonomy only |
| WDC Products / Large-Scale Product Corpus | 26M offers, 16M clusters, 4,400 labelled gold pairs, JSON, CC BY | **Yes** |
| Abt-Buy, Amazon-Google, DBLP-ACM (Leipzig) | Clean CSV, CC BY 4.0, fixed train/valid/test splits | **Yes** |
| Walmart-Amazon (via DeepMatcher repo) | 10,242 pairs, 962 positive | **Yes** |
| [Alaska benchmark](https://github.com/merialdo/research.alaska) | Camera 29,787 records/103 entities, Monitor 16,662/232, Notebook 23,167/208. MIT | **Yes**, entity *and* schema matching |
| eprocure.gov.in / CPPP | ~27,585 live tenders, no login, BOQ as text-extractable PDF | No |
| bidplus.gem.gov.in | Real buyer bid postings, free-text item descriptions, server-rendered | No |

**Alaska is the best structural proxy** among the benchmarks: 20+ heterogeneous sources
with wildly varying attribute schemas is much closer to cross-CPSE material-master
heterogeneity than flat retail listing pairs.

> ⚠️ **UNSPSC licence:** the UNGM file is **personal use only**, no commercial or public use,
> no redistribution. Prototyping only. The official Excel costs $275.

## Dead ends — do not spend an afternoon here

- **NMCRL** — subscription-gated, no bulk download
- **GSA NSN extract** — only 12,455 rows, no CAGE or part-number cross-reference
- **nsncenter.com, nsnsearch.com, nsnpartnumber.com, wbparts.com** — all dead ends
- **Indian Railways** iMMS / UDM / PL numbers — internal CRIS systems, only user manuals are
  public. IREPS item-master endpoints redirect to a login wall
- **GeM bulk catalogue** — reports page 404s, `dashboard.gem.gov.in` does not resolve, the
  marketplace is an Angular SPA with no export. The 3 GeM-tagged datasets on data.gov.in are
  aggregate stats only (933 bytes)
- **data.gov.in** — **zero** IOCL/BPCL/HPCL/ONGC/NTPC/SAIL/Coal India/CPCL material, stores
  or procurement datasets under any search term tried
- **Manufacturer catalogues** — McMaster-Carr robots.txt disallows `/catalog/*` and its API
  needs certificate auth; Grainger and Fastenal return edge-level 403s; Misumi robots.txt is
  a blanket `Disallow: /`; SKF is a JS-rendered SPA; TraceParts is login-gated with
  no-redistribution terms. **EngineersEdge explicitly blocks `ClaudeBot` and `GPTBot` by
  name.** Do not scrape these
- **DBLP-ACM** — real and labelled but bibliographic, useless for us

## Academic work

- **PhRAG** ([arXiv:2606.03367](https://arxiv.org/abs/2606.03367), SUPSI, 2026) — the single
  most on-topic paper, builds a spare-parts pooling system. Code is public, **evaluation
  dataset is proprietary**, which confirms our premise that real data stays private
- **FabNER** — 350K+ words of manufacturing text, but it is NER, wrong task type
- **SAP SALT** (HuggingFace, CC-BY-NC-SA-4.0, 4.26M rows) — real anonymised ERP data, but
  sales orders, not material master, and no dedup labels
- **OAEI 2025 "Beyond Equivalence"** track — industrial taxonomy alignment across
  GPC/UNSPSC/ETIM/eCl@ss with explicit equivalence links, but at **category** level, not
  item-instance level
- Kaggle/Zenodo "parts" datasets are uniformly **computer vision**, not text

## The three-layer strategy to adopt

| Layer | Data | What it licenses us to claim |
|---|---|---|
| **1. Prove the algorithm** | FLIS for real "many codes, one item" ground truth; WDC / Abt-Buy / Alaska as standard benchmarks | Real precision and recall against externally validated labels |
| **2. Prove the domain** | eprocure/CPPP and GeM bidplus BOQ text, hand-label 50–100 pairs | Authentic Indian procurement text. Say it is **our own** clustering, not an external benchmark |
| **3. Prove the edge cases** | Synthetic bolts seeded from published standards | Controlled demo cases that behave identically every rehearsal. Report as a **designed ceiling** |

State all three limits out loud rather than blending them into one number. A CPCL evaluator
notices.
