"""The blanks a reviewer is asked to fill.

Separate from the review queue on purpose. The queue is about deciding relationships between
records; this is about completing the records themselves. One answer here can clear dozens of
queued pairs, so it is ranked by how much each answer is worth.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from samepart.api import schemas as s
from samepart.api.deps import question_service
from samepart.services.protocols import QuestionService

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=s.QuestionPage)
def questions(request: Request, cursor: str | None = None, limit: int = Query(50, ge=1, le=200),
              svc: QuestionService = Depends(question_service)):
    p = getattr(request.state, "principal", None)
    return svc.questions(cursor, limit, p.org if p and p.role == "steward" else None)


@router.post("/records/{record_id}/unresolvable", response_model=s.AnswerResult)
def unresolvable(record_id: int, req: s.UnresolvableRequest, request: Request,
                 svc: QuestionService = Depends(question_service)):
    """Declare that a blank cannot be answered from any source, so it stops being asked."""
    try:
        p = getattr(request.state, "principal", None)
        if p is not None:
            req.reviewer, req.reviewer_role, req.reviewer_org = p.actor_name, p.role, p.org
        return svc.unresolvable(record_id, req)
    except KeyError:
        raise HTTPException(404, f"no record with id {record_id}")
    except PermissionError as exc:
        # 403: the person is not wrong, they are not the one who can say.
        raise HTTPException(403, str(exc))


@router.post("/records/{record_id}/answer", response_model=s.AnswerResult)
def answer(record_id: int, req: s.AnswerRequest, request: Request,
           svc: QuestionService = Depends(question_service)):
    try:
        p = getattr(request.state, "principal", None)
        if p is not None:
            req.reviewer, req.reviewer_role, req.reviewer_org = p.actor_name, p.role, p.org
        return svc.answer(record_id, req)
    except KeyError:
        raise HTTPException(404, f"no record with id {record_id}")
    except PermissionError as exc:
        # 403: the person is not wrong, they are not the one who can say.
        raise HTTPException(403, str(exc))
