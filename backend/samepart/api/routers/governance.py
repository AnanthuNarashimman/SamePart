"""Who may decide, what was decided, and how to undo it."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from samepart.api import schemas as s
from samepart.api.deps import governance_service
from samepart.services.protocols import GovernanceService

router = APIRouter(tags=["governance"])


@router.get("/governance", response_model=s.GovernanceInfo)
def info(svc: GovernanceService = Depends(governance_service)):
    """Roles, the default posture, and whether automation is currently on."""
    return svc.info()


@router.get("/audit", response_model=s.AuditTrail)
def audit(cursor: str | None = None, limit: int = Query(50, ge=1, le=500),
          actor: str | None = None, action: str | None = None,
          svc: GovernanceService = Depends(governance_service)):
    """The append-only decision log. Nothing here is ever updated or deleted."""
    return svc.audit(cursor, limit, actor, action)


@router.get("/governance/egress")
def egress(limit: int = Query(50, ge=1, le=500), blocked_only: bool = False):
    """Every outbound call the system attempted, sent or blocked, and what was in it.

    A blocked entry is the useful one. It shows exactly what would have left the network and
    confirms that it did not, which is the evidence a security review asks for.
    """
    from samepart.model.egress import LEDGER

    entries = [e for e in reversed(LEDGER.entries) if not (blocked_only and e.allowed)]
    return {
        **LEDGER.summary(),
        "entries": [
            {"at": e.at, "destination": e.destination, "purpose": e.purpose,
             "allowed": e.allowed, "bytes": e.bytes_out, "sha256_16": e.digest,
             "note": e.note, "payload": e.payload}
            for e in entries[:limit]
        ],
    }


@router.post("/canonical/{canonical_id}/reverse", response_model=s.ReverseResult)
def reverse(canonical_id: str, req: s.ReverseRequest,
            svc: GovernanceService = Depends(governance_service)):
    """Undo a mapping. Deletes a cross-reference row; alters no CPSE material code."""
    try:
        return svc.reverse(canonical_id, req)
    except KeyError:
        raise HTTPException(404, f"no canonical material {canonical_id}")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
