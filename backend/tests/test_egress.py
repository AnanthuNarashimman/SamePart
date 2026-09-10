"""The egress guard, which is a sovereignty claim expressed as code.

"CPSE data must not leave the network" is the constraint the whole deployment posture rests
on. If the default ever flips, nothing fails, no metric moves, and the claim quietly becomes
false while the demo keeps working. That is the exact failure mode a test exists for.
"""
import pytest

from samepart.model import egress


@pytest.fixture(autouse=True)
def clean_ledger(monkeypatch):
    monkeypatch.delenv("SAMEPART_ALLOW_EXTERNAL", raising=False)
    egress.LEDGER.entries.clear()
    yield
    egress.LEDGER.entries.clear()


def test_outbound_calls_are_blocked_unless_explicitly_permitted():
    """The default, and the only one that matters. Absence of configuration must mean no."""
    assert egress.external_allowed() is False
    with pytest.raises(egress.EgressBlocked):
        egress.guard("api.example.com", "attribute extraction", "M16X80 A2-70")


def test_a_blocked_attempt_is_still_recorded_with_its_payload():
    """Refusing silently would be worse than sending. A reviewer has to be able to see what
    would have left, which is the difference between a control and a promise."""
    with pytest.raises(egress.EgressBlocked):
        egress.guard("api.example.com", "attribute extraction", "M16X80 A2-70 ISO4014")

    assert len(egress.LEDGER.entries) == 1
    attempt = egress.LEDGER.entries[0]
    assert attempt.allowed is False
    assert "M16X80" in attempt.payload

    summary = egress.LEDGER.summary()
    assert summary["blocked"] == 1
    assert summary["sent"] == 0


def test_permission_is_opt_in_and_takes_effect(monkeypatch):
    monkeypatch.setenv("SAMEPART_ALLOW_EXTERNAL", "1")
    assert egress.external_allowed() is True
    egress.guard("api.example.com", "attribute extraction", "M16X80")
    assert egress.LEDGER.summary()["sent"] == 1


def test_the_blocked_message_says_how_to_proceed():
    """An error that does not name the switch it wants leaves someone guessing at a demo."""
    with pytest.raises(egress.EgressBlocked) as raised:
        egress.guard("api.example.com", "extraction", "payload")
    assert "SAMEPART_ALLOW_EXTERNAL" in str(raised.value)
