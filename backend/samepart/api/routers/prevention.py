"""Duplicate prevention at the moment of creation.

The cheapest place to fix a duplicate is before it exists. Reuses the same comparison the
reconciliation desk uses, against the full canonical set rather than a batch.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from samepart.api import schemas as s
from samepart.api.deps import check_service
from samepart.services.protocols import CheckService

router = APIRouter(tags=["prevention"])


@router.post("/check", response_model=s.CheckResult)
def check(req: s.CheckRequest, svc: CheckService = Depends(check_service)):
    return svc.check(req)
