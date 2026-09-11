"""The baseline comparison, which is only persuasive if it is not rigged.

Every number in `baselines.py` argues that the alternatives to this project are worse, which
makes it the one module where a bug flatters us and nobody notices. These check the parts that
would silently do that: a sweep that reports the wrong operating point, a baseline that loses
because of a scoring mistake rather than on the merits, and the two matched-operating-point
selectors that the whole comparison rests on.
"""
import numpy as np
import pytest

from samepart.evaluation.baselines import (
    FLOOR, Point, _at_least_precision, _at_least_recall, _jaccard_matrix, _sweep, _trigrams,
)


def point(precision: float, recall: float) -> Point:
    return Point(threshold=0.5, precision=precision, recall=recall, f1=0.0, merges=0,
                 false_merges=0, hard_negative_merges=0, hard_negative_rate=0.0)


# ── scoring ─────────────────────────────────────────────────────────────────────────────


def test_identical_text_scores_one():
    m = _jaccard_matrix([_trigrams("HEX BOLT M20X40"), _trigrams("HEX BOLT M20X40")])
    assert m[0, 1] == pytest.approx(1.0)


def test_similarity_is_symmetric():
    """Asymmetry would mean a pair's score depended on which record came first."""
    m = _jaccard_matrix([_trigrams("BOLT M20"), _trigrams("Bolt, Hexagon, M20 x 40mm")])
    assert m[0, 1] == pytest.approx(m[1, 0])


def test_unrelated_text_scores_near_zero():
    m = _jaccard_matrix([_trigrams("gasket spiral wound"), _trigrams("BEARING 6205 ZZ")])
    assert m[0, 1] < 0.15


def test_trigrams_survive_house_style_differences():
    """The reason the trigram baseline is the strong one, and why it has to be included.

    A token matcher scores these near zero; a character matcher does not. Leaving it out would
    have meant beating only the weakest alternative.
    """
    trigram = _jaccard_matrix([_trigrams("M20X40"), _trigrams("M20 x 40")])[0, 1]
    token = _jaccard_matrix([["m20x40"], ["m20", "x", "40"]])[0, 1]
    assert trigram > token


# ── the sweep ───────────────────────────────────────────────────────────────────────────


def test_a_perfect_scorer_reaches_precision_and_recall_of_one():
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    truth = np.array([True, True, False, False])
    hard = np.array([False, False, True, True])

    best = max(_sweep(scores, truth, hard, total_true=2), key=lambda p: p.f1)
    assert best.precision == pytest.approx(1.0)
    assert best.recall == pytest.approx(1.0)
    assert best.false_merges == 0


def test_recall_counts_true_pairs_the_scorer_never_saw():
    """A pair below the floor is still a pair the baseline failed to find.

    Measuring recall over only the pairs that cleared a threshold is the standard way an
    entity-resolution benchmark flatters itself, and it would flatter the baselines here.
    """
    scores = np.array([0.9])
    truth = np.array([True])
    hard = np.array([False])

    best = max(_sweep(scores, truth, hard, total_true=10), key=lambda p: p.f1)
    assert best.recall == pytest.approx(0.1)


def test_a_scorer_that_finds_nothing_reports_zero_rather_than_nothing():
    """This was a real defect: an empty curve printed a dash where a 0.0000 belonged.

    Exact text matching finds no pair at all in the catalogue, which is the single most useful
    number in the table, and it was being rendered as though the baseline had failed to run.
    """
    curve = _sweep(np.array([FLOOR / 2]), np.array([True]), np.array([False]), total_true=1)
    assert len(curve) == 1
    assert curve[0].precision == 0.0
    assert curve[0].recall == 0.0


def test_every_point_is_reachable_by_some_threshold():
    """Tied scores cannot be split, so a point inside a run of equal scores is not an option.

    Reporting one would mean quoting a precision no threshold can actually produce.
    """
    scores = np.array([0.8, 0.8, 0.8, 0.3])
    truth = np.array([True, False, False, True])
    curve = _sweep(scores, truth, np.array([False, True, True, False]), total_true=2)

    for p in curve:
        merged = scores >= p.threshold
        assert p.merges == int(merged.sum())


def test_hard_negative_rate_is_over_all_hard_negatives_not_the_merged_ones():
    scores = np.array([0.9, 0.9])
    truth = np.array([False, False])
    hard = np.array([True, True])

    # Only one of the two hard negatives is merged at the tightest threshold... but both share
    # a score, so the only reachable point merges both.
    curve = _sweep(scores, truth, hard, total_true=1)
    assert curve[-1].hard_negative_rate == pytest.approx(1.0)


# ── matched operating points ────────────────────────────────────────────────────────────


def test_at_our_recall_picks_the_most_precise_point_that_still_reaches_it():
    curve = [point(0.9, 0.4), point(0.6, 0.6), point(0.3, 0.9)]
    assert _at_least_recall(curve, 0.55).precision == pytest.approx(0.6)


def test_at_our_recall_is_none_when_the_baseline_cannot_reach_it():
    assert _at_least_recall([point(0.9, 0.2)], 0.55) is None


def test_at_our_precision_picks_the_highest_recall_point_that_is_still_safe():
    curve = [point(0.99, 0.1), point(0.98, 0.3), point(0.5, 0.9)]
    assert _at_least_precision(curve, 0.98).recall == pytest.approx(0.3)


def test_at_our_precision_is_none_when_no_threshold_is_safe_enough():
    """The headline claim: no string or embedding baseline reaches our precision anywhere.

    If this ever returns a point for a real baseline, that claim is false and the table must
    stop making it.
    """
    assert _at_least_precision([point(0.4, 0.9), point(0.7, 0.5)], 0.98) is None
