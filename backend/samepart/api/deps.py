"""Dependency wiring.

SAMEPART_MODE selects the implementation. `stub` returns fixtures so the frontend is never
blocked; `live` uses the real pipeline. Each service switches independently, so the backend
can go live one endpoint at a time without the frontend changing anything.
"""
from __future__ import annotations

import os

from samepart.services import stub
from samepart.services.protocols import (AnalyticsService, CatalogueService, CheckService,
                                         FamilyService, ReviewService)

MODE = os.getenv("SAMEPART_MODE", "stub")


def catalogue_service() -> CatalogueService:
    return stub.StubCatalogue()


def review_service() -> ReviewService:
    return stub.StubReview()


def check_service() -> CheckService:
    return stub.StubCheck()


def analytics_service() -> AnalyticsService:
    return stub.StubAnalytics()


def family_service() -> FamilyService:
    return stub.StubFamilies()
