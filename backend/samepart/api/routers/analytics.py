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


@router.get("/analytics/rationalisation", response_model=s.RationalisationResult)
def rationalisation(limit: int = 100, svc: AnalyticsService = Depends(analytics_service)):
    """Legacy material code rationalisation: codes nobody has ordered in the window."""
    return svc.rationalisation(limit)


@router.get("/analytics/audit-flags", response_model=s.AuditFlagResult)
def audit_flags(limit: int = 50, svc: AnalyticsService = Depends(analytics_service)):
    """Merges the system nominates for a second look, based on evidence it never used."""
    return svc.audit_flags(limit)
