"""Organisations and catalogue import."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from samepart.api import schemas as s
from samepart.api.deps import catalogue_service
from samepart.services.protocols import CatalogueService

router = APIRouter(tags=["catalogue"])


@router.get("/orgs", response_model=list[s.Org])
def list_orgs(svc: CatalogueService = Depends(catalogue_service)):
    return svc.list_orgs()


@router.post("/orgs", response_model=s.Org, status_code=201)
def create_org(org: s.Org, svc: CatalogueService = Depends(catalogue_service)):
    return svc.create_org(org.code, org.name)


@router.post("/imports/preview", response_model=s.ImportPreview)
async def preview_import(file: UploadFile = File(...), kind: str = Form("catalogue")):
    """Read the headers and propose a column mapping. Nothing is imported."""
    from samepart.config import settings
    from samepart.ingest.column_detect import ColumnDetector, preview

    if kind not in ("catalogue", "procurement"):
        raise HTTPException(400, "kind must be 'catalogue' or 'procurement'")
    detector = ColumnDetector.from_file(settings.dictionary_dir / "column_aliases.yaml")
    result = preview(await file.read(), detector, kind)

    required = ("source_code", "description") if kind == "catalogue" \
        else ("source_code", "po_number", "po_date")
    missing = [f for f in required if f not in result["column_map"]]
    return s.ImportPreview(
        kind=kind, headers=result["headers"], sample_rows=result["sample_rows"],
        suggestions=[s.ColumnSuggestion(**vars(x)) for x in result["suggestions"]],
        column_map=result["column_map"], ready=not missing, missing_required=missing)


@router.post("/imports", response_model=s.ImportStatus, status_code=202)
async def start_import(
    file: UploadFile = File(...),
    org_code: str = Form(...),
    family: str = Form("hex_bolt"),
    column_map: str = Form("{}"),
    svc: CatalogueService = Depends(catalogue_service),
):
    try:
        mapping = json.loads(column_map)
    except json.JSONDecodeError:
        raise HTTPException(400, "column_map must be valid JSON")
    content = await file.read()
    req = s.ImportRequest(org_code=org_code, family=family, column_map=mapping)
    return svc.start_import(req, file.filename or "upload.csv", content)


@router.get("/imports/{import_id}", response_model=s.ImportStatus)
def import_status(import_id: str, svc: CatalogueService = Depends(catalogue_service)):
    return svc.import_status(import_id)
