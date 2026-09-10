"""The egress guard.

"We are careful with your data" is not an answer a security review accepts. "Outbound calls
are structurally blocked, and here is the complete record of what the system would have sent"
is.

Two things happen here.

1. **A hard block.** When external calls are not permitted, the call is not attempted. This
   is not a warning or a default that a stray environment variable can undo; the request
   never reaches the network layer.
2. **A record either way.** Blocked or allowed, every outbound attempt is written to the
   ledger with its destination, purpose, size and a digest of the exact bytes. A blocked
   entry is the useful one: it lets an auditor see precisely what would have left, and
   confirm that it did not.

The default is **blocked**. A CPSE turns egress on deliberately, having read the ledger,
rather than discovering after the fact that it was on all along.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


def external_allowed() -> bool:
    return os.getenv("SAMEPART_ALLOW_EXTERNAL", "0").strip().lower() in ("1", "true", "yes")


def keep_payloads() -> bool:
    """Whether the ledger keeps the bytes themselves, not only their digest."""
    return os.getenv("SAMEPART_EGRESS_KEEP_PAYLOAD", "1").strip().lower() in ("1", "true", "yes")


@dataclass
class EgressAttempt:
    at: datetime
    destination: str
    purpose: str
    allowed: bool
    bytes_out: int
    digest: str
    payload: str | None = None
    note: str = ""


@dataclass
class EgressLedger:
    entries: list[EgressAttempt] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, destination: str, purpose: str, payload: str,
               allowed: bool, note: str = "") -> EgressAttempt:
        raw = payload.encode("utf-8", errors="replace")
        entry = EgressAttempt(
            at=datetime.now(timezone.utc), destination=destination, purpose=purpose,
            allowed=allowed, bytes_out=len(raw),
            digest=hashlib.sha256(raw).hexdigest()[:16],
            payload=payload if keep_payloads() else None, note=note)
        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > 2000:
                del self.entries[:-2000]
        return entry

    def summary(self) -> dict:
        blocked = sum(1 for e in self.entries if not e.allowed)
        sent = len(self.entries) - blocked
        return {
            "policy": "external calls permitted" if external_allowed()
                      else "external calls blocked",
            "allow_external": external_allowed(),
            "attempts": len(self.entries),
            "sent": sent,
            "blocked": blocked,
            "bytes_sent": sum(e.bytes_out for e in self.entries if e.allowed),
            "bytes_withheld": sum(e.bytes_out for e in self.entries if not e.allowed),
            "destinations": sorted({e.destination for e in self.entries}),
        }


LEDGER = EgressLedger()


class EgressBlocked(RuntimeError):
    """Raised instead of making a call that policy does not permit."""


def guard(destination: str, purpose: str, payload: str) -> None:
    """Record the attempt, and refuse it if policy says so."""
    allowed = external_allowed()
    LEDGER.record(destination, purpose, payload, allowed,
                  note="" if allowed else "not sent; SAMEPART_ALLOW_EXTERNAL is off")
    if not allowed:
        raise EgressBlocked(
            f"Outbound call to {destination} for {purpose} was blocked. The exact payload is "
            f"recorded in the egress ledger and can be reviewed. Set "
            f"SAMEPART_ALLOW_EXTERNAL=1 to permit it, or configure a local model instead.")
