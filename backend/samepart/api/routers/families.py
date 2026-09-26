"""Material families: what is loaded, add one, fetch one to start from.

Adding a family is the national approver's act. A steward can read the list and download a
file, which is all a steward needs to draft one for the approver to load.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from samepart.api import schemas as s
from samepart.api.deps import family_service
from samepart.services.protocols import FamilyService

router = APIRouter(tags=["families"])


@router.get("/families", response_model=list[s.FamilySummary])
def list_families(svc: FamilyService = Depends(family_service)):
    return svc.list_families()


@router.get("/families/{name}/yaml", response_class=PlainTextResponse)
def family_yaml(name: str, svc: FamilyService = Depends(family_service)):
    try:
        return svc.family_yaml(name)
    except KeyError:
        raise HTTPException(404, f"no family named {name!r}")


@router.post("/families", response_model=s.FamilyLoadResult, status_code=201)
def load_family(request: Request, replace: bool = False,
                yaml_text: str = Body(..., media_type="text/plain"),
                svc: FamilyService = Depends(family_service)):
    p = getattr(request.state, "principal", None)
    if p is not None and p.role != "national_approver":
        raise HTTPException(403, "only the national codification approver may add a family; "
                                 "a steward can draft one and hand it over")
    try:
        return svc.load_family(yaml_text, actor=p.actor_name if p else "system", replace=replace)
    except FileExistsError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
