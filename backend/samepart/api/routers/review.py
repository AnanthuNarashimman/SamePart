"""The reconciliation desk: queue, comparison, decision."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

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
    request: Request = None,
    svc: ReviewService = Depends(review_service),
):
    if group and group not in GROUPS:
        raise HTTPException(400, f"unknown group {group!r}; expected one of {sorted(GROUPS)}")
    p = getattr(request.state, "principal", None)
    return svc.queue(group, cursor, limit, p.role if p else None, p.org if p else None)


@router.get("/matches/{match_id}", response_model=s.MatchDetail)
def match(match_id: int, svc: ReviewService = Depends(review_service)):
    try:
        return svc.match(match_id)
    except KeyError:
        raise HTTPException(404, f"no match with id {match_id}")


@router.post("/matches/{match_id}/decision", response_model=s.DecisionResult)
def decide(match_id: int, req: s.DecisionRequest, request: Request,
           svc: ReviewService = Depends(review_service)):
    # The seat is the token's. Whatever the body says about who is deciding is replaced.
    p = getattr(request.state, "principal", None)
    if p is not None:
        req.reviewer, req.reviewer_role, req.reviewer_org = p.actor_name, p.role, p.org
    try:
        return svc.decide(match_id, req)
    except KeyError:
        raise HTTPException(404, f"no match with id {match_id}")
    except PermissionError as exc:
        # 403, not 500. The reviewer did nothing wrong; they lack the authority.
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc))
