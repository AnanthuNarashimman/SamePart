"""Tamper evidence for the decision trail.

The trail was already append-only in the sense that nothing in the application updates or
deletes a `decision_event` row. That is a property of our code, and it stops being true the
moment somebody opens the database file. For a national identifier that is not enough: a
CPSE has to be able to show that the record of who approved what has not been edited after
the fact, including by us.

Each event carries the SHA-256 of its own contents together with the hash of the event before
it, so the rows form a chain. Changing any field of any past event, or deleting one, or
inserting one between two others, breaks every hash from that point on and `verify` names the
first row where the chain parts.

This is deliberately not a blockchain and makes no distributed claim. It is the same
construction a tamper-evident log has used for decades: cheap, verifiable with one pass, and
honest about what it proves — that the trail has not been altered *since it was written*, not
that what was written was true.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from samepart.db.models import DecisionEvent

GENESIS = "0" * 64


def _timestamp(at: datetime | None) -> str | None:
    """One canonical spelling of an instant, whatever the driver hands back.

    The hash has to be computed over the STORED form, not the in-memory one. SQLite returns a
    naive datetime even when an aware one was written, so sealing a row and then verifying it
    produced two different strings for the same instant and the chain failed on its own first
    event. Everything is normalised to UTC and written without an offset.
    """
    if at is None:
        return None
    if at.tzinfo is not None:
        at = at.astimezone(timezone.utc).replace(tzinfo=None)
    return at.isoformat(timespec="microseconds")


def digest(event: DecisionEvent, prev_hash: str) -> str:
    """The hash of one event, bound to the one before it.

    Field order is fixed and the payload is serialised with sorted keys, because a hash over a
    dict whose key order can vary is a hash that fails at random.
    """
    body = json.dumps(
        {
            "id": event.id,
            "pair_id": event.pair_id,
            "canonical_id": event.canonical_id,
            "actor": event.actor,
            "action": event.action,
            "payload": event.payload,
            "at": _timestamp(event.at),
            "prev_hash": prev_hash,
        },
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def head(db, before_id: int | None = None) -> str:
    """The hash of the last event before `before_id`, which the next one chains onto.

    The exclusion matters. Sealing happens after the row is flushed so it has an id, which
    means the row being sealed is already the newest one in the table — without `before_id`
    every event would chain onto itself, read its own empty hash, and record GENESIS.
    """
    query = select(DecisionEvent).order_by(DecisionEvent.id.desc()).limit(1)
    if before_id is not None:
        query = (select(DecisionEvent).where(DecisionEvent.id < before_id)
                 .order_by(DecisionEvent.id.desc()).limit(1))
    last = db.scalars(query).first()
    return last.entry_hash if last and last.entry_hash else GENESIS


def seal(db, event: DecisionEvent) -> DecisionEvent:
    """Chain a newly written event onto the trail.

    Requires the row to have an id, so the caller flushes first. Hashing before the id exists
    would mean hashing a different object than the one stored.
    """
    event.prev_hash = head(db, before_id=event.id)
    event.entry_hash = digest(event, event.prev_hash)
    return event


@dataclass
class ChainStatus:
    events: int
    intact: bool
    broken_at: int | None = None
    reason: str = ""

    def as_dict(self) -> dict:
        return {"events": self.events, "intact": self.intact,
                "broken_at": self.broken_at, "reason": self.reason}


def verify(db) -> ChainStatus:
    """Walk the trail in order and report the first link that does not hold."""
    prev = GENESIS
    seen = 0

    for event in db.scalars(select(DecisionEvent).order_by(DecisionEvent.id)):
        seen += 1

        # Events written before the chain existed carry no hash. They are reported rather
        # than silently accepted: an unsealed row is not evidence of tampering, but it is not
        # evidence of integrity either.
        if not event.entry_hash:
            return ChainStatus(seen, False, event.id,
                               "event has no hash; it predates the audit chain or was "
                               "inserted directly into the database")

        if event.prev_hash != prev:
            return ChainStatus(seen, False, event.id,
                               f"expected to follow {prev[:12]}… but records {(event.prev_hash or '')[:12]}…; "
                               "an event was inserted, removed or reordered")

        expected = digest(event, event.prev_hash)
        if event.entry_hash != expected:
            return ChainStatus(seen, False, event.id,
                               f"contents hash to {expected[:12]}… but the row records "
                               f"{event.entry_hash[:12]}…; this event was edited after it was written")

        prev = event.entry_hash

    return ChainStatus(seen, True)
