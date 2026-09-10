"""The audit chain, which is only worth having if it actually detects tampering.

A tamper-evident log that nobody has tried to tamper with is a claim, not a control. Each of
these performs the edit an attacker — or an embarrassed operator — would actually make, and
asserts the chain notices: changing who approved a merge, deleting an inconvenient decision,
and inserting one that never happened.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from samepart import audit
from samepart.db.models import Base, DecisionEvent


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def write(db, actor: str, action: str, payload: dict, minute: int) -> DecisionEvent:
    """Write one event the way the service does: flush for an id, then seal."""
    event = DecisionEvent(
        actor=actor, action=action, payload=payload,
        at=datetime(2026, 9, 10, 12, minute, tzinfo=timezone.utc))
    db.add(event)
    db.flush()
    audit.seal(db, event)
    db.flush()
    return event


@pytest.fixture
def trail(db):
    write(db, "steward-a", "approve_same", {"canonical_id": "IN-0000001-5"}, 1)
    write(db, "steward-b", "approve_different", {"reason": "grade differs"}, 2)
    write(db, "national-approver", "approve_same", {"canonical_id": "IN-0000002-3"}, 3)
    db.flush()
    return db


def test_an_untouched_trail_verifies(trail):
    status = audit.verify(trail)
    assert status.intact, status.reason
    assert status.events == 3


def test_the_first_event_chains_onto_genesis(trail):
    first = trail.get(DecisionEvent, 1)
    assert first.prev_hash == audit.GENESIS
    assert first.entry_hash


def test_editing_who_approved_a_merge_is_detected(trail):
    """The edit somebody would actually make: reassign an approval to a different person."""
    event = trail.get(DecisionEvent, 2)
    event.actor = "someone-else"
    trail.flush()

    status = audit.verify(trail)
    assert not status.intact
    assert status.broken_at == 2
    assert "edited after it was written" in status.reason


def test_editing_a_payload_is_detected(trail):
    """Changing what was decided, while leaving who and when alone."""
    event = trail.get(DecisionEvent, 3)
    event.payload = {**(event.payload or {}), "canonical_id": "IN-9999999-9"}
    trail.flush()

    assert not audit.verify(trail).intact


def test_backdating_an_event_is_detected(trail):
    event = trail.get(DecisionEvent, 1)
    event.at = event.at - timedelta(days=30)
    trail.flush()

    assert not audit.verify(trail).intact


def test_deleting_an_inconvenient_decision_is_detected(trail):
    """Removal breaks the link in the event that followed it, so a gap cannot be hidden."""
    trail.delete(trail.get(DecisionEvent, 2))
    trail.flush()

    status = audit.verify(trail)
    assert not status.intact
    assert status.broken_at == 3
    assert "inserted, removed or reordered" in status.reason


def test_an_unsealed_row_inserted_directly_is_detected(trail):
    """A row written straight into the database, bypassing the application entirely."""
    trail.add(DecisionEvent(actor="ghost", action="approve_same", payload={},
                            at=datetime(2026, 9, 10, 12, 4, tzinfo=timezone.utc)))
    trail.flush()

    status = audit.verify(trail)
    assert not status.intact
    assert "no hash" in status.reason


def test_a_resealed_forgery_still_fails_because_the_chain_moved_on(trail):
    """The one an attacker would try next: edit an event and recompute its own hash.

    It fails because the following event's `prev_hash` still records the original value, so
    covering the edit means resealing every event after it too — which is exactly the cost a
    hash chain is meant to impose.
    """
    event = trail.get(DecisionEvent, 2)
    event.actor = "someone-else"
    event.entry_hash = audit.digest(event, event.prev_hash)
    trail.flush()

    status = audit.verify(trail)
    assert not status.intact
    assert status.broken_at == 3


def test_an_empty_trail_is_intact_not_broken(db):
    """Nothing to verify is not a failure. A fresh database must not report tampering."""
    status = audit.verify(db)
    assert status.intact
    assert status.events == 0


def test_every_decision_event_writer_goes_through_record(db):
    """A structural check, because this failed silently once.

    Three services constructed a DecisionEvent and added it directly, so the chain broke the
    first time anyone declared a value unresolvable, supplied an attribute, or reversed a
    merge. Nothing caught it: the only path exercised was the baseline reviewer, which sealed
    correctly. Grepping the source is a blunt test and a fair one — the failure mode is
    somebody adding a fourth writer.
    """
    from pathlib import Path

    source = Path("backend/samepart/services/live.py").read_text()
    assert "DecisionEvent(" not in source, (
        "a service constructs DecisionEvent directly; use audit.record so it is chained")


def test_record_chains_a_written_event(db):
    from samepart.db.models import DecisionEvent

    audit.record(db, actor="steward", action="approve_same", payload={"a": 1})
    audit.record(db, actor="steward", action="mapping_reversed", payload={"b": 2})
    db.flush()

    events = list(db.scalars(__import__("sqlalchemy").select(DecisionEvent)
                             .order_by(DecisionEvent.id)))
    assert [e.prev_hash for e in events] == [audit.GENESIS, events[0].entry_hash]
    assert audit.verify(db).intact
