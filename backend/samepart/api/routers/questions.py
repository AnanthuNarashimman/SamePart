"""The blanks a reviewer is asked to fill.

Separate from the review queue on purpose. The queue is about deciding relationships between
records; this is about completing the records themselves. One answer here can clear dozens of
queued pairs, so it is ranked by how much each answer is worth.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from samepart.api import schemas as s
from samepart.api.deps import question_service
from samepart.services.protocols import QuestionService

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=s.QuestionPage)
def questions(cursor: str | None = None, limit: int = Query(50, ge=1, le=200),
              svc: QuestionService = Depends(question_service)):
    return svc.questions(cursor, limit)


@router.post("/records/{record_id}/answer", response_model=s.AnswerResult)
def answer(record_id: int, req: s.AnswerRequest,
           svc: QuestionService = Depends(question_service)):
    try:
        return svc.answer(record_id, req)
    except KeyError:
        raise HTTPException(404, f"no record with id {record_id}")
