"""Getting the result back out, into the systems of record.

Capability 8 is integration and capability 5 is migration support, and both come down to the
same thing: a CPSE has to be able to load this into what it already runs. Nothing here
alters a source material code.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from samepart.api import schemas as s
from samepart.api.deps import export_service
from samepart.services.protocols import ExportService

router = APIRouter(tags=["export"])


@router.get("/export/cross-reference", response_model=s.CrossReferenceExport)
def cross_reference(org_code: str | None = None, limit: int = Query(5000, ge=1, le=50000),
                    svc: ExportService = Depends(export_service)):
    """Every CPSE code with its national reference. The CPSE's code is never altered."""
    return svc.cross_reference(org_code, limit)


@router.get("/export/cross-reference.csv")
def cross_reference_csv(org_code: str | None = None,
                        svc: ExportService = Depends(export_service)):
    """The same thing as a file a stores team can open and a loader can read."""
    data = svc.cross_reference(org_code, 50000)
    buf = io.StringIO()
    fields = ["org_code", "source_code", "national_code", "canonical_identity",
              "classification_code", "standardised_short", "base_uom", "status",
              "duplicate_of", "approved_by"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in data.items:
        writer.writerow(row.model_dump())
    buf.seek(0)
    name = f"samepart_crossreference_{org_code or 'all'}.csv"
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/export/migration-plan", response_model=s.MigrationPlan)
def migration_plan(svc: ExportService = Depends(export_service)):
    """Legacy rationalisation: what to keep, collapse, close, and send to a person."""
    return svc.migration_plan()


@router.get("/export/erp/{canonical_id}")
def erp_payload(canonical_id: str, svc: ExportService = Depends(export_service)):
    """A material master payload shaped like the interface an SAP team expects."""
    try:
        return svc.erp_payload(canonical_id)
    except KeyError:
        raise HTTPException(404, f"no canonical material {canonical_id}")
