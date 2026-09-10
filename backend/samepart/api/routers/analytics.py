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


@router.get("/analytics/redistribution", response_model=s.RedistributionReport)
def redistribution(idle_days: int = 365, limit: int = 50,
                   svc: AnalyticsService = Depends(analytics_service)):
    """Stock one CPSE already holds that another is actively buying.

    Impossible without cross-organisation identity: neither party can see it today, because
    each describes the same item differently and their systems cannot tell they match.
    """
    return svc.redistribution(idle_days, limit)


@router.get("/analytics/cascade", response_model=s.CascadeBreakdown)
def cascade(svc: AnalyticsService = Depends(analytics_service)):
    """Which tier settled each pair. Most never reach a model."""
    return svc.cascade_breakdown()


@router.get("/analytics/price-spread", response_model=s.PriceSpreadReport)
def price_spread(limit: int = 12, svc: AnalyticsService = Depends(analytics_service)):
    """What each CPSE paid per base unit for the same canonical material."""
    return svc.price_spread(limit)


@router.get("/analytics/stock-ageing", response_model=s.StockAgeing)
def stock_ageing(idle_days: int = 365, svc: AnalyticsService = Depends(analytics_service)):
    """How long stock on hand has gone without a goods issue."""
    return svc.stock_ageing(idle_days)


@router.get("/analytics/audit-flags", response_model=s.AuditFlagResult)
def audit_flags(limit: int = 50, svc: AnalyticsService = Depends(analytics_service)):
    """Merges the system nominates for a second look, based on evidence it never used."""
    return svc.audit_flags(limit)
