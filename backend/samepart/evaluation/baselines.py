"""What a straightforward implementation of this problem would have achieved.

The obvious objection to this project is that material-code harmonisation is a string-matching
exercise, and that fuzzy matching or a sentence embedding would get most of the way there for
a fraction of the machinery. It is a fair objection and it deserves a measured answer rather
than an assertion, so this runs those alternatives over exactly the same records, the same
labels and the same metrics as `harness.evaluate`.

Three things make the comparison honest rather than a strawman:

  Tuned in their favour.  Each baseline is swept across its whole threshold range and reported
                          at the operating point that maximises its own F1. That threshold was
                          chosen by looking at the answers, which is a luxury no deployment
                          gets. The baselines are therefore shown at their ceiling and ours is
                          not.
  Matched operating points.  A matcher can always buy precision with recall, so comparing two
                          systems at whatever thresholds they happen to sit on says nothing.
                          Each baseline is also reported at the threshold where it retrieves
                          as much as we do, and at the threshold where it is as safe as we
                          are. Those are the two comparisons a plant actually cares about.
  Counted, not averaged.  The headline is false merges at matched recall — how many wrong
                          parts this approach would have put in front of a buyer to find the
                          same duplicates we find.

None of the baselines can abstain, because none of them have anything to abstain about: a
similarity score has no notion of a fact being missing. That is not a handicap we imposed, it
is the property that makes them unsuitable for the decision, and the table shows its cost.
"""
from __future__ import annotations

import itertools
import os
import random
import re
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select

from samepart.db.models import CandidateMatch, SourceRecord

Pair = tuple[int, int]

# Scores below this are never anyone's operating point; dropping them keeps the sweep cheap
# without altering any reported figure, since every baseline's best F1 sits far above it.
FLOOR = 0.05


@dataclass
class Point:
    """One operating point on a baseline's curve."""
    threshold: float
    precision: float
    recall: float
    f1: float
    merges: int
    false_merges: int
    hard_negative_merges: int
    hard_negative_rate: float

    def as_dict(self) -> dict:
        return {
            "threshold": round(self.threshold, 4), "precision": round(self.precision, 4),
            "recall": round(self.recall, 4), "f1": round(self.f1, 4), "merges": self.merges,
            "false_merges": self.false_merges,
            "hard_negative_merges": self.hard_negative_merges,
            "hard_negative_rate": round(self.hard_negative_rate, 4),
        }


@dataclass
class Baseline:
    name: str
    what: str
    best_f1: Point | None = None
    at_our_recall: Point | None = None
    at_our_precision: Point | None = None
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name, "what": self.what, "note": self.note,
            "best_f1": self.best_f1.as_dict() if self.best_f1 else None,
            "at_our_recall": self.at_our_recall.as_dict() if self.at_our_recall else None,
            "at_our_precision": self.at_our_precision.as_dict() if self.at_our_precision else None,
        }


@dataclass
class Comparison:
    records: int = 0
    true_pairs: int = 0
    candidate_pairs: int = 0
    hard_negatives: int = 0
    ours: dict = field(default_factory=dict)
    baselines: list[Baseline] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "records": self.records, "true_pairs": self.true_pairs,
            "candidate_pairs": self.candidate_pairs,
            "hard_negatives": self.hard_negatives, "ours": self.ours,
            "baselines": [b.as_dict() for b in self.baselines], "notes": self.notes,
        }


# ── the baselines themselves ────────────────────────────────────────────────────────────
#
# Each returns a dense upper-triangular score matrix over the record list. Dense is the right
# choice here and would not be at scale: 1,600 records is 1.3 million pairs, which numpy holds
# in five megabytes. A real deployment would block first; these are being asked what they can
# do at their best, so they are given every pair.

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _trigrams(text: str) -> list[str]:
    s = re.sub(r"\s+", " ", text.lower().strip())
    return [s[i:i + 3] for i in range(max(0, len(s) - 2))] or [s]


def _jaccard_matrix(documents: list[list[str]]) -> np.ndarray:
    """Jaccard over a binary presence matrix, which is a matrix product and a broadcast.

    Presence rather than count is deliberate: this is the similarity a `rapidfuzz`-style token
    matcher computes, and inflating it with term weighting would be modelling something the
    baseline does not do.
    """
    vocabulary = {t: i for i, t in enumerate({t for d in documents for t in d})}
    m = np.zeros((len(documents), len(vocabulary)), dtype=np.float32)
    for row, doc in enumerate(documents):
        for t in doc:
            m[row, vocabulary[t]] = 1.0

    intersection = m @ m.T
    sizes = m.sum(axis=1)
    union = sizes[:, None] + sizes[None, :] - intersection
    return np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)


def _exact(records: list[SourceRecord]) -> np.ndarray:
    """The floor: identical descriptions after whitespace and case normalisation.

    Worth measuring because it is what a spreadsheet deduplication actually does, and because
    its recall is the honest size of the part of this problem that needs no intelligence.
    """
    keys = [re.sub(r"\s+", " ", x.raw_description.lower().strip()) for x in records]
    index = {k: i for i, k in enumerate(sorted(set(keys)))}
    codes = np.array([index[k] for k in keys])
    return (codes[:, None] == codes[None, :]).astype(np.float32)


def _fuzzy_tokens(records: list[SourceRecord]) -> np.ndarray:
    return _jaccard_matrix([_tokens(x.raw_description) for x in records])


def _fuzzy_trigrams(records: list[SourceRecord]) -> np.ndarray:
    """Character n-grams, which is what most off-the-shelf fuzzy matchers score on.

    Unlike whole tokens it survives the formatting differences that separate one CPSE's house
    style from another's — `M20X40` against `M20 x 40` — so it is the stronger of the two
    string baselines and the one to beat.
    """
    return _jaccard_matrix([_trigrams(x.raw_description) for x in records])


def _embedding(records: list[SourceRecord]) -> np.ndarray:
    """A sentence embedding over the raw description, cosine similarity, no attributes.

    This is the architecture most entries in this problem space actually ship: encode the
    description, threshold the cosine. It is given the raw text on purpose, because a system
    that could produce the canonical form has already done the typed extraction that is the
    thing under test.
    """
    from samepart.pipeline.embeddings import LocalEmbedder

    vectors = LocalEmbedder().encode([x.raw_description for x in records])
    return (vectors @ vectors.T).astype(np.float32)


SCORERS = [
    ("exact_text", "Identical descriptions after case and whitespace normalisation", _exact),
    ("fuzzy_tokens", "Token-set Jaccard over the raw description", _fuzzy_tokens),
    ("fuzzy_trigrams", "Character 3-gram Jaccard over the raw description", _fuzzy_trigrams),
    ("embedding", "Sentence-embedding cosine over the raw description", _embedding),
]


# ── sweeping ────────────────────────────────────────────────────────────────────────────


def _sweep(scores: np.ndarray, truth: np.ndarray, hard: np.ndarray,
           total_true: int) -> list[Point]:
    """Every distinct operating point of one baseline, in one pass.

    Sorting the pairs by score and accumulating gives the whole precision/recall curve without
    re-thresholding the matrix, and means the reported best-F1 point is genuinely the best
    rather than the best of a handful of round numbers somebody guessed.
    """
    keep = scores >= FLOOR
    s, t, h = scores[keep], truth[keep], hard[keep]
    if s.size == 0:
        # A baseline that never scores anything above the floor has not failed to run; it has
        # answered, and the answer is that it finds nothing. Returning an empty curve would
        # print a dash where the most damning number in the table belongs.
        return [Point(threshold=1.0, precision=0.0, recall=0.0, f1=0.0, merges=0,
                      false_merges=0, hard_negative_merges=0, hard_negative_rate=0.0)]

    order = np.argsort(-s, kind="stable")
    s, t, h = s[order], t[order].astype(np.int64), h[order].astype(np.int64)

    merges = np.arange(1, s.size + 1)
    tp = np.cumsum(t)
    hard_merged = np.cumsum(h)

    # Only the last index of each run of equal scores is a real threshold; the ones inside a
    # run describe a cut no threshold can make.
    edge = np.append(s[1:] != s[:-1], True)
    idx = np.flatnonzero(edge)

    precision = tp[idx] / merges[idx]
    recall = tp[idx] / total_true if total_true else np.zeros_like(precision)
    denominator = precision + recall
    f1 = np.divide(2 * precision * recall, denominator,
                   out=np.zeros_like(precision), where=denominator > 0)
    hard_total = int(hard.sum())

    return [
        Point(
            threshold=float(s[i]), precision=float(precision[j]), recall=float(recall[j]),
            f1=float(f1[j]), merges=int(merges[i]),
            false_merges=int(merges[i] - tp[i]),
            hard_negative_merges=int(hard_merged[i]),
            hard_negative_rate=float(hard_merged[i] / hard_total) if hard_total else 0.0,
        )
        for j, i in enumerate(idx)
    ]


def _at_least_recall(curve: list[Point], target: float) -> Point | None:
    """The safest point that still finds as much as we do — the tightest threshold clearing it."""
    reaching = [p for p in curve if p.recall >= target]
    return max(reaching, key=lambda p: p.precision) if reaching else None


def _at_least_precision(curve: list[Point], target: float) -> Point | None:
    """The most productive point that is still as safe as we are."""
    safe = [p for p in curve if p.precision >= target]
    return max(safe, key=lambda p: p.recall) if safe else None


# ── entry point ─────────────────────────────────────────────────────────────────────────


def compare(db, *, family: str | None = None, llm_sample: int = 0) -> Comparison:
    from samepart.evaluation.harness import evaluate

    c = Comparison()

    records = [x for x in db.scalars(select(SourceRecord)) if x.truth_identity]
    if family:
        records = [x for x in records if x.family == family]
    records.sort(key=lambda x: x.id)
    n = len(records)
    c.records = n
    if n < 2:
        c.notes.append("Fewer than two labelled records; nothing to compare.")
        return c

    position = {x.id: i for i, x in enumerate(records)}
    index = {t: i for i, t in enumerate(sorted({x.truth_identity for x in records}))}
    identity = np.array([index[x.truth_identity] for x in records])
    truth_matrix = (identity[:, None] == identity[None, :])

    upper = np.triu(np.ones((n, n), dtype=bool), k=1)
    truth = truth_matrix[upper]
    c.true_pairs = int(truth.sum())

    # Every baseline is handed our candidate pairs and scored only on those.
    #
    # This is a concession, and a deliberate one. Turned loose on all 1.3 million pairs a
    # trigram matcher will happily merge a bolt with a bearing, which makes for a flattering
    # table and a worthless argument — nobody would deploy it that way. Giving them our
    # blocking for free costs them no recall (pairs completeness is 1.00, so every true pair
    # is in the set) and enormously improves their precision, and it isolates the only
    # question worth asking: given the same pairs to judge, who judges them better. The
    # unblocked figure is still computed and reported as a note, because the gap between the
    # two is itself the measure of how much the blocking is doing.
    candidate_matrix = np.zeros((n, n), dtype=bool)
    for m in db.scalars(select(CandidateMatch)):
        i, j = position.get(m.a_id), position.get(m.b_id)
        if i is not None and j is not None:
            candidate_matrix[i, j] = candidate_matrix[j, i] = True
    candidates = candidate_matrix[upper]

    # Hard negatives, defined exactly as the harness defines them: pairs our blocking thought
    # were worth comparing that turned out to be different materials.
    hard = candidates & ~truth
    c.hard_negatives = int(hard.sum())
    c.candidate_pairs = int(candidates.sum())

    ours = evaluate(db, family=family)
    pairwise = ours.decision.get("pairwise", {})
    c.ours = {
        "precision": pairwise.get("precision", 0.0),
        "recall": pairwise.get("recall", 0.0),
        "f1": pairwise.get("f1", 0.0),
        "merges": pairwise.get("tp", 0) + pairwise.get("fp", 0),
        "false_merges": ours.decision.get("false_merges", 0),
        "hard_negative_merges": ours.hard_negatives.get("wrongly_merged", 0),
        "hard_negative_rate": ours.hard_negatives.get("false_merge_rate", 0.0),
        "abstained": ours.decision.get("abstained", 0),
        "abstention_rate": ours.decision.get("abstention_rate", 0.0),
        "model_share": round(1 - ours.tiers.get("share_without_a_model", 1.0), 4),
    }

    for name, what, score in SCORERS:
        try:
            matrix = score(records)
        except Exception as exc:  # a missing optional dependency must not void the whole table
            c.baselines.append(Baseline(name=name, what=what, note=f"not run: {exc}"))
            continue

        flat = matrix[upper]
        curve = _sweep(flat[candidates], truth[candidates], hard[candidates], c.true_pairs)
        unblocked = _sweep(flat, truth, hard, c.true_pairs)
        best_unblocked = max(unblocked, key=lambda p: p.f1)

        c.baselines.append(Baseline(
            name=name, what=what,
            best_f1=max(curve, key=lambda p: p.f1),
            at_our_recall=_at_least_recall(curve, c.ours["recall"]),
            at_our_precision=_at_least_precision(curve, c.ours["precision"]),
            note=("threshold chosen with the answers in hand; without our blocking its best "
                  f"precision falls to {best_unblocked.precision:.4f} "
                  f"({best_unblocked.false_merges:,} false merges)"),
        ))

    if llm_sample:
        hard_matrix = candidate_matrix & ~truth_matrix
        c.baselines.append(_llm_only(db, records, truth_matrix, hard_matrix, llm_sample, c))

    c.notes.append(
        "No baseline abstains: a similarity score cannot represent a fact being absent, so "
        f"every pair is forced to a yes or a no. Ours declines {c.ours['abstained']} pairs "
        "and routes them to a person.")
    return c


def _llm_only(db, records, truth_matrix, hard_matrix, sample: int, c: Comparison) -> Baseline:
    """Ask a model directly, with no extraction, no gates and no dictionary.

    The question this answers is the one every evaluator asks: why not just show the two
    descriptions to GPT? It runs on a balanced sample rather than the full set because the
    full set is 1.3 million calls, and the sample is stratified over true pairs and hard
    negatives so the reported rate is not an artefact of how rare true pairs are.
    """
    from samepart.model.client import get_model

    baseline = Baseline(
        name="llm_only", what="A model shown two raw descriptions, no attributes or gates")

    model = get_model()
    if not model.available:
        baseline.note = "not run: no model configured (set SAMEPART_MODE=live)"
        return baseline

    n = len(records)
    rng = random.Random(20260911)
    true_pairs, hard_pairs = [], []
    for i, j in itertools.combinations(range(n), 2):
        if truth_matrix[i, j]:
            true_pairs.append((i, j))
        elif hard_matrix[i, j]:
            hard_pairs.append((i, j))

    half = max(1, sample // 2)
    chosen = (rng.sample(true_pairs, min(half, len(true_pairs)))
              + rng.sample(hard_pairs, min(half, len(hard_pairs))))
    rng.shuffle(chosen)

    system = ("You decide whether two material descriptions from different company catalogues "
              "refer to the same physical material. Reply with JSON: {\"same\": true|false}.")

    tp = fp = fn = merges = hard_merged = 0
    failures = 0
    for i, j in chosen:
        # 400 rather than the 64 a yes/no answer needs. The endpoint is a reasoning model, so
        # a tight budget is spent thinking and the call returns an empty string having never
        # reached the answer. At 64 it failed on 35% of pairs, and those failures were not
        # random — the pairs it thought hardest were exactly the ones it could not afford to
        # finish, so the surviving sample was the easy half and the score flattered it.
        reply = model.json(
            system,
            f"A: {records[i].raw_description}\nB: {records[j].raw_description}",
            max_tokens=400)
        if not reply.ok:
            failures += 1
            continue
        said_same = bool(reply.data.get("same"))
        actually_same = bool(truth_matrix[i, j])
        if said_same:
            merges += 1
            tp += actually_same
            fp += not actually_same
            hard_merged += bool(hard_matrix[i, j])
        else:
            fn += actually_same

    answered = len(chosen) - failures
    if not answered:
        baseline.note = f"not run: the model failed on all {len(chosen)} sampled pairs"
        return baseline

    sample_precision = tp / merges if merges else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    hard_seen = sum(1 for i, j in chosen if hard_matrix[i, j])
    hard_rate = hard_merged / hard_seen if hard_seen else 0.0

    # The sample is balanced; the catalogue is not. Reporting the balanced precision in a
    # column beside ours would be comparing a rate measured on a 50/50 set against one measured
    # on a set that is four-fifths hard negatives, and the balanced figure would win on the
    # arithmetic alone. Rescaling to the real prevalence is the only way the two numbers mean
    # the same thing: apply the measured true-pair recall and hard-negative merge rate to the
    # counts actually in the catalogue.
    true_total = int(truth_matrix[np.triu(np.ones_like(truth_matrix), k=1).astype(bool)].sum())
    hard_total = int(hard_matrix[np.triu(np.ones_like(hard_matrix), k=1).astype(bool)].sum())
    est_tp = recall * true_total
    est_fp = hard_rate * hard_total
    precision = est_tp / (est_tp + est_fp) if est_tp + est_fp else 0.0

    baseline.best_f1 = Point(
        threshold=float("nan"), precision=precision, recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        merges=round(est_tp + est_fp), false_merges=round(est_fp),
        hard_negative_merges=round(est_fp), hard_negative_rate=hard_rate)
    baseline.note = (
        f"{answered} of {len(chosen)} sampled pairs answered ({failures} failed), balanced "
        f"between true pairs and hard negatives. On the sample itself precision was "
        f"{sample_precision:.4f}; the figure shown is that sample's recall and hard-negative "
        f"rate rescaled to the catalogue's real {true_total:,}/{hard_total:,} split, which is "
        f"the only form comparable to the other rows. It also needs one model call for every "
        f"pair it judges, where ours reaches a model on "
        f"{c.ours['model_share']:.1%} of them.")
    return baseline


def allowed_to_run_a_model() -> bool:
    """The LLM baseline is the only part of this that leaves the machine."""
    return os.getenv("SAMEPART_MODE", "stub") == "live"
