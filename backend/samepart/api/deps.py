"""Dependency wiring.

`SAMEPART_MODE` selects implementations. `stub` returns fixtures so the frontend is never
blocked. `live` uses the database and pipeline. Services flip **independently**: anything
without a live implementation yet stays on its stub, and the frontend cannot tell.
"""
from __future__ import annotations

import os
from functools import lru_cache

from samepart.config import settings
from samepart.dictionary.loader import Dictionary, load_dictionary
from samepart.services import live, stub
from samepart.services.protocols import (AnalyticsService, CatalogueService, CheckService,
                                         FamilyService, QuestionService, ReviewService)


def mode() -> str:
    return os.getenv("SAMEPART_MODE", "stub").lower()


@lru_cache(maxsize=1)
def dictionary() -> Dictionary:
    """Loaded once at first use. Families, units, gates and blocking all come from YAML."""
    return load_dictionary(settings.dictionary_dir)


def catalogue_service() -> CatalogueService:
    if mode() == "live":
        return live.LiveCatalogue(dictionary())
    return stub.StubCatalogue()


def review_service() -> ReviewService:
    if mode() == "live":
        return live.LiveReview(dictionary())
    return stub.StubReview()


def question_service() -> QuestionService:
    if mode() == "live":
        return live.LiveQuestions(dictionary())
    return stub.StubQuestions()


def check_service() -> CheckService:
    return stub.StubCheck()           # step 7


def analytics_service() -> AnalyticsService:
    if mode() == "live":
        return live.LiveAnalytics(dictionary())
    return stub.StubAnalytics()


def family_service() -> FamilyService:
    return stub.StubFamilies()        # step 9


def live_services() -> list[str]:
    """Reported at /api/health so the frontend can see what is real yet."""
    return ["catalogue", "review", "questions", "analytics"] if mode() == "live" else []
