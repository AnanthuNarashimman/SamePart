"""Conflict gates and the cascade's automation refusal.

These are the safety properties. The evaluation harness measures how often the system is
right; these check that when it is wrong, it is wrong in the safe direction — abstaining
rather than merging, and never merging on a model's say-so.

Precedence in particular cannot be measured in aggregate: a gate table that resolves
"same and different" to `same` would still score well on a dataset where the case is rare,
and would be catastrophic on the one pair where it mattered.
"""
from pathlib import Path

import pytest

from samepart.api.deps import dictionary
from samepart.gates import Verdict, evaluate
from samepart.pipeline import cascade

FAMILY = dictionary().family("hex_bolt")


def attrs(**kw):
    """Attributes in the shape the gates expect: key -> value, absent means not stated."""
    return dict(kw)


def test_a_differing_critical_attribute_forces_different():
    """Two bolts of different diameter are not the same bolt, whatever the text similarity
    says. This is the case a pure language model gets wrong."""
    a = attrs(thread_diameter_mm=16, length_mm=100, grade="8.8", head_type="HEX", finish="PLAIN")
    b = attrs(thread_diameter_mm=20, length_mm=100, grade="8.8", head_type="HEX", finish="PLAIN")

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME)
    assert outcome.verdict is Verdict.DIFFERENT


def test_a_declared_substitution_downgrades_a_critical_conflict_rather_than_rejecting_it():
    """8.8 against 10.9 is a critical difference AND a declared substitution, and the
    dictionary wins.

    The family says 10.9 may stand in for 8.8 where the joint is not designed for controlled
    yield, so the honest answer is neither "same" nor "different" but "interchangeable under
    this condition" — and the condition travels with the verdict. Asserting DIFFERENT here
    would have been asserting that the substitution table does not work.
    """
    a = attrs(thread_diameter_mm=20, length_mm=100, grade="8.8", head_type="HEX", finish="PLAIN")
    b = attrs(thread_diameter_mm=20, length_mm=100, grade="10.9", head_type="HEX", finish="PLAIN")

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME)
    assert outcome.verdict is Verdict.POSSIBLE_ALTERNATIVE
    assert outcome.substitution_conditions, "a substitute verdict must carry its condition"
    assert "controlled yield" in " ".join(outcome.substitution_conditions)


def test_a_missing_critical_attribute_forces_abstention():
    """Unknown is not the same as equal. The system asks rather than assuming."""
    a = attrs(thread_diameter_mm=12, length_mm=60, grade="8.8")
    b = attrs(thread_diameter_mm=12, length_mm=60)          # grade never stated

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME)
    assert outcome.verdict is Verdict.INSUFFICIENT_EVIDENCE


def test_a_settled_blank_stops_the_missing_gate_re_asking():
    """Once a person has established that a value does not exist anywhere, asking again
    forever is how a review queue becomes permanent."""
    a = attrs(thread_diameter_mm=12, length_mm=60, grade="8.8")
    b = attrs(thread_diameter_mm=12, length_mm=60)

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME, settled={"grade"})
    assert outcome.verdict is not Verdict.INSUFFICIENT_EVIDENCE


def test_conflict_beats_agreement_when_both_gates_fire():
    """Precedence, the property that cannot be seen in an aggregate score.

    A pair can trip the identity gate (same part number) and the critical-conflict gate (a
    differing grade) at once. Resolving that to `same` would merge two materials on the
    strength of a part number that is evidently wrong. The safe resolution is to refuse.
    """
    a = attrs(manufacturer="ANV", manufacturer_part_number="HB1660",
              thread_diameter_mm=16, length_mm=60, grade="8.8")
    b = attrs(manufacturer="ANV", manufacturer_part_number="HB1660",
              thread_diameter_mm=16, length_mm=60, grade="12.9")

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME)
    assert outcome.verdict is not Verdict.SAME, (
        "a contradicting pair of gates must never resolve to a merge")


def test_standards_declared_equivalent_compare_as_equal():
    """DIN 931 was superseded by ISO 4014 and the family declares them `equivalent`, so a
    record citing either is citing the same specification. Equivalence is a stronger claim
    than substitutability and it collapses the difference entirely."""
    a = attrs(thread_diameter_mm=16, length_mm=60, grade="8.8", standard="ISO4014")
    b = attrs(thread_diameter_mm=16, length_mm=60, grade="8.8", standard="DIN931")

    assert evaluate(FAMILY, a, b, incoming=Verdict.SAME).verdict is Verdict.SAME


def test_a_major_difference_with_no_equivalence_becomes_a_substitute():
    """ISO 4014 against IS 1364 is a real specification difference with no equivalence
    declared, so the identities stay separate — the third answer the problem statement asks
    for, and the one a two-way matcher cannot express."""
    a = attrs(thread_diameter_mm=16, length_mm=60, grade="8.8", standard="ISO4014")
    b = attrs(thread_diameter_mm=16, length_mm=60, grade="8.8", standard="IS1364")

    outcome = evaluate(FAMILY, a, b, incoming=Verdict.SAME)
    assert outcome.verdict is Verdict.POSSIBLE_ALTERNATIVE


def test_a_model_verdict_is_never_auto_mergeable():
    """The rule that keeps the problem statement's user-validation requirement satisfied once
    inference enters the pipeline. Automation is allowed only where nothing is being judged,
    and a model is called precisely because something is."""
    policy = FAMILY.auto_merge.model_copy(update={"enabled": True, "require_all_known": False,
                                                  "require_score": 0.0})
    result = cascade.CascadeResult(
        verdict=Verdict.SAME, decided_by="model", score=1.0, proposal=Verdict.SAME,
        gate=evaluate(FAMILY, attrs(thread_diameter_mm=16), attrs(thread_diameter_mm=16)),
        rationale="model said so")

    assert result.auto_mergeable(policy) is False


def test_automation_is_off_by_default_in_every_family():
    """The posture the problem statement describes: a workflow that lets a person approve.
    A family shipping with automation on would change that silently."""
    for name, family in dictionary().families.items():
        assert family.auto_merge.enabled is False, f"{name} ships with auto-merge enabled"
