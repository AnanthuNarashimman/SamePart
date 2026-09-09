"""Read-only reporting over decisions already made."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from samepart.api import schemas as s
from samepart.api.deps import analytics_service
from samepart.services.protocols import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary", response_model=s.AnalyticsSummary)
def summary(svc: AnalyticsService = Depends(analytics_service)):
    return svc.summary()


@router.get("/analytics/savings", response_model=s.SavingsResult)
def savings(svc: AnalyticsService = Depends(analytics_service)):
    return svc.savings()
