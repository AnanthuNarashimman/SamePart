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
