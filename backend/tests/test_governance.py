"""The two-tier rule, exercised the way the desk exercises it.

The interesting property is political rather than technical: one organisation's steward may
decide about that organisation's codes and nothing else, and the moment two organisations'
codes are called one material is reserved for an authority both recognise. These check the
rulings the service consults, including the one that was never reached before the frontend
started saying who was asking.
"""
from samepart import governance as gov


def test_a_steward_decides_within_their_own_organisation():
    assert gov.may_decide("steward", {"BPCL"}, "BPCL").allowed


def test_a_steward_cannot_decide_a_cross_organisation_pair():
    ruling = gov.may_decide("steward", {"BPCL", "NTPC"}, "BPCL")
    assert not ruling.allowed
    assert ruling.required_role == "national_approver"
    assert "national identifier" in ruling.reason


def test_a_steward_cannot_decide_another_organisations_pair():
    ruling = gov.may_decide("steward", {"NTPC"}, "BPCL")
    assert not ruling.allowed
    assert "NTPC" in ruling.reason


def test_the_national_approver_decides_across_organisations():
    assert gov.may_decide("national_approver", {"BPCL", "NTPC"}).allowed


def test_a_viewer_decides_nothing():
    assert not gov.may_decide("viewer", {"BPCL"}, "BPCL").allowed


def test_a_steward_answers_only_for_their_own_records():
    assert gov.may_answer("steward", "BPCL", "BPCL").allowed
    ruling = gov.may_answer("steward", "NTPC", "BPCL")
    assert not ruling.allowed
    assert "only NTPC knows" in ruling.reason


def test_the_national_approver_may_answer_for_anyone():
    assert gov.may_answer("national_approver", "NTPC").allowed


def test_the_audit_name_says_which_organisation_in_which_role():
    assert gov.actor_name("steward", "BPCL") == "BPCL-steward"
    assert gov.actor_name("national_approver", None) == "national-approver"
