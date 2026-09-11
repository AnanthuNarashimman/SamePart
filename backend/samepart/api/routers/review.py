"""The reconciliation desk: queue, comparison, decision."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from samepart.api import schemas as s
from samepart.api.deps import review_service
from samepart.services.protocols import ReviewService

router = APIRouter(tags=["review"])

GROUPS = {"needs_input", "possible_alternative", "same_material", "different"}


@router.get("/queue", response_model=s.QueuePage)
def queue(
    group: str | None = Query(None, description=f"One of {sorted(GROUPS)}"),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    actor_role: str | None = Query(None, description="Scope the queue to what this role may act on"),
    actor_org: str | None = Query(None, description="The steward's own CPSE"),
    svc: ReviewService = Depends(review_service),
):
    if group and group not in GROUPS:
        raise HTTPException(400, f"unknown group {group!r}; expected one of {sorted(GROUPS)}")
    return svc.queue(group, cursor, limit, actor_role, actor_org)


@router.get("/matches/{match_id}", response_model=s.MatchDetail)
def match(match_id: int, svc: ReviewService = Depends(review_service)):
    try:
        return svc.match(match_id)
    except KeyError:
        raise HTTPException(404, f"no match with id {match_id}")


@router.post("/matches/{match_id}/decision", response_model=s.DecisionResult)
def decide(match_id: int, req: s.DecisionRequest, svc: ReviewService = Depends(review_service)):
    try:
        return svc.decide(match_id, req)
    except KeyError:
        raise HTTPException(404, f"no match with id {match_id}")
    except PermissionError as exc:
        # 403, not 500. The reviewer did nothing wrong; they lack the authority.
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc))
