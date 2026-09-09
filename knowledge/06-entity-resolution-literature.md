# The literature that arms us

Our plan worries, correctly, about being dismissed as "just a wrapper." It then never cites
the work that answers the charge. Every position below is defensible from published results,
and together they fill the Research & References slide that is currently empty.

## Our four-way verdict is not novel — and that is good news

**Fellegi & Sunter, "A Theory for Record Linkage" (JASA, 1969)** does not output a binary.
It defines two thresholds on a likelihood-ratio weight, producing **three regions**: link,
**possible link routed to clerical review**, and non-link.

Abstention in entity matching is **the original 1969 design**, 55 years before "selective
prediction" was named in machine learning.

- **Chow's rule (1970)** — the reject option: predict only when confidence is sufficiently
  high, otherwise abstain
- **El-Yaniv & Wiener (JMLR 2010)** — formalises the risk-coverage tradeoff
- **Geifman & El-Yaniv (NeurIPS 2017)** — selective classification for deep networks
- **Calibration:** Platt scaling and isotonic regression (Niculescu-Mizil & Caruana, ICML
  2005); conformal prediction for distribution-free coverage guarantees (Angelopoulos &
  Bates, [arXiv:2107.07511](https://arxiv.org/pdf/2107.07511))

**Do not claim** we invented abstention in entity matching.
**Do claim** novelty in *application*: calibrated or conformal abstention on a
language-model matcher for **industrial** records is barely published.

## Splink is the strongest free asset we are not using

[moj-analytical-services/splink](https://github.com/moj-analytical-services/splink) — MIT
licence, built by the **UK Ministry of Justice**.

- Implements Fellegi-Sunter with **EM parameter estimation**, so it needs **no labelled
  training data** — which matters enormously, because CPSE material master data has no
  ground truth
- Outputs a **calibrated match probability** per pair
- Runs on DuckDB, Spark or Athena; reports linking around **1 million records in about a
  minute on a laptop**

Use it as the deterministic tier **and** as the published baseline our model must beat.

**Licence warning on the obvious alternative:** Zingg is **AGPL v3**, a real constraint if
we ever redistribute. `dedupe` (MIT) and Python Record Linkage Toolkit (BSD-3) are
permissive. JedAI (Apache-2.0) has the best meta-blocking implementation.

## Published numbers to position against

| System | Result |
|---|---|
| **Ditto** (VLDB 2021, [arXiv:2004.00584](https://arxiv.org/abs/2004.00584)) | Beats DeepMatcher in all 13 benchmark cases, by up to 29–31 F1; **F1 96.5** matching 789K and 412K company records |
| **HierGAT** (SIGMOD 2022) | Up to 32.5 F1 over DeepMatcher, up to 8.7 over Ditto |
| **Peeters, Steiner & Bizer** ([arXiv:2310.11244](https://arxiv.org/abs/2310.11244), EDBT 2025) | Zero-shot LLMs beat the best *transferred* PLM matcher by **≥8 F1**; GPT-4 by **40–68 F1**. Fine-tuning adds 1–26 F1 more |

That last one is direct published support for our LLM comparator path. It converts "just a
wrapper" into "the published state of the art for this task class."

## The on-premises answer, with a number

**OpenSanctions Pairs** ([arXiv:2603.11051](https://arxiv.org/abs/2603.11051)) — 755,540
expert-labelled pairs over 1M entities, 293 sources, 45 jurisdictions.

| Matcher | F1 |
|---|---|
| Rule-based baseline | 91.3 |
| GPT-4o | 99.0 |
| **Distilled 14B open model** | **98.2** |

Losing under a point to keep CPSE data inside the refinery network is an argument we win in
one sentence.

**Jellyfish 7B/13B** (EMNLP 2024, [arXiv:2312.01678](https://arxiv.org/abs/2312.01678),
open weights on HuggingFace) is instruction-tuned specifically for data-preprocessing tasks
including entity matching, and runs fully on-premises.

Reported LLM failure modes to be honest about: hallucinated justifications, prompt and
serialisation sensitivity, and cross-script transliteration errors.

## Blocking at scale

Naive all-pairs is O(n²) — for 2M records that is roughly 2×10¹² pairs.

- Standard blocking, sorted neighbourhood, canopy clustering (McCallum et al., KDD 2000),
  MinHash/LSH
- **DeepBlocker** (VLDB 2021) — self-supervised, no labels, fastText plus FAISS
- Transformer-embedding blocking reports roughly **15% higher recall** than DeepBlocker on
  most benchmarks ([arXiv:2304.12329](https://arxiv.org/pdf/2304.12329))

**Report the standard protocol:** Pairs Completeness (recall of true matches retained) and
Reduction Ratio (comparisons eliminated), per Papadakis et al., ACM CSUR 2020
([arXiv:1905.06167](https://arxiv.org/pdf/1905.06167)).

## Clustering: pairwise decisions do not compose transitively

- **Connected components** is single-linkage — one spurious high-scoring edge chains two
  true clusters together. Splink implements this directly.
- **Correlation clustering** (Bansal, Blum, Chawla, 2004) is the theoretically correct
  framing. NP-hard, constant-factor approximation available.
- **Markov Clustering** (van Dongen, 2000) resists chaining because flow must be reinforced
  by multiple paths.
- **Our "cluster safety" rule is a cannot-link constraint** from constrained clustering.
  Name it that way.

Standard survey citation: Getoor & Machanavajjhala, VLDB 2012.

## Active learning: our review queue is already generating training data

- **Zingg** publishes **30–50 labelled pairs** to reach a usable model
- **dedupe** documents a minimum of 10 positive and 10 negative pairs
- Academic anchor: Arasu, Götz & Kaushik, SIGMOD 2010

Nothing in our plan feeds reviewer decisions back. That is a flywheel we are throwing away.

**Note:** Splink is *not* an active-learning tool. Its EM estimation is unsupervised; labels
there serve only calibration and accuracy assessment.

## Evaluation: report the right metrics, honestly

- **Pairwise** precision/recall/F1 — standard, but over- or under-penalises depending on
  cluster-size distribution
- **B-cubed** (Bagga & Baldwin, 1998) — element-wise cluster metric, the one to add
- Also MUC, CEAF, Adjusted Rand Index
- **Operational metrics:** percentage auto-resolved, precision **of the auto-merge tier
  specifically**, reviewer hours saved

> **Honesty requirement:** synthetic F1 is **inflated by construction**, because we designed
> the corruption distribution and tuned against it. Report it as a labelled *ceiling*
> number, never as production accuracy. If we get any real labelled subset, report it
> separately rather than blending.

## Attribute extraction and taxonomy classification

- **OpenTag** (KDD 2018, [arXiv:1806.01264](https://arxiv.org/abs/1806.01264)) — open
  attribute value extraction as sequence tagging, built for unseen values
- **AVEQA** (KDD 2020) — multi-task QA framing, attribute name as the question. The right
  shape when there are hundreds of possible attributes
- **MAVE** (WSDM 2022) — 2.2M products, 3M annotations, but **consumer e-commerce, not
  industrial**

**UNSPSC classification, expected accuracy shape**
([arXiv:2503.04728](https://arxiv.org/pdf/2503.04728)): top LLMs reach roughly **80% at
6-digit** granularity and **over 90% at 2-digit**. A TF-IDF + SVM approach on government
procurement spend reports ~93%. **Report accuracy per hierarchy level** — that is what this
literature does.

**Two genuine gaps we can claim carefully:**

1. Industrial and MRO attribute extraction has **no published benchmark**. The e-commerce
   literature is mature; industrial technical text is thin. We are not failing to beat a
   baseline, because there isn't one.
2. **eCl@ss classification literature is essentially empty.** Any numbers we report there
   are first-of-kind, not a reproduction.

Novelty in application is an honest claim. Novelty in the mathematics is not.
