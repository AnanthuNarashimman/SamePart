"""Material families. Powers the live new-family bootstrap demo."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from samepart.api import schemas as s
from samepart.api.deps import family_service
from samepart.services.protocols import FamilyService

router = APIRouter(tags=["families"])


@router.get("/families", response_model=list[s.FamilySummary])
def list_families(svc: FamilyService = Depends(family_service)):
    return svc.list_families()


@router.post("/families", response_model=s.FamilyLoadResult, status_code=201)
def load_family(yaml_text: str = Body(..., media_type="text/plain"),
                svc: FamilyService = Depends(family_service)):
    return svc.load_family(yaml_text)
