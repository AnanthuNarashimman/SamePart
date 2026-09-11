"""Application factory.

Routers are registered here and nowhere else. Each router is small, owns one concern, and
depends on a service protocol rather than on the pipeline, so replacing a stub with the
real implementation touches one file.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from samepart import auth as auth_module

from samepart.api.deps import live_services, mode
from samepart.api.routers import (analytics, auth, catalogue, export, families,
                                  governance, prevention, questions, review)

DESCRIPTION = """
Cross-organisation material identity resolution.

Every comparison resolves to one of four verdicts, never a forced binary:
`same_material`, `possible_alternative`, `different`, or `insufficient_evidence`.

Source codes are never overwritten. A canonical identity is an additional row.
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title="SamePart API",
        version="0.1.0",
        description=DESCRIPTION,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )

    # Wide open during development so the Vite dev server on any port can call it.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Everything under /api needs a signed token except the door itself and the health
    # check. The principal is attached to the request; routers that write take the role
    # from it and never from the body.
    OPEN = {"/api/health", "/api/auth/login"}

    @app.middleware("http")
    async def require_signed_in(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api") and path not in OPEN and request.method != "OPTIONS":
            header = request.headers.get("authorization", "")
            principal = auth_module.verify(header.removeprefix("Bearer ").strip()) if header else None
            if principal is None:
                return JSONResponse({"detail": "Sign in to continue."}, status_code=401)
            request.state.principal = principal
        return await call_next(request)

    auth_module.announce()
    for r in (auth, catalogue, review, questions, prevention, analytics, export,
              governance, families):
        app.include_router(r.router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    def health():
        from samepart.model.client import get_model
        from samepart.model.egress import LEDGER, external_allowed

        model = get_model()
        on_host = getattr(model, "on_host", False)
        return {
            "status": "ok", "mode": mode(), "live_services": live_services(),
            "model": {
                "name": model.name, "available": model.available,
                "runs_on_host": bool(on_host),
                "data_leaves_network": bool(model.available and not on_host
                                            and external_allowed()),
            },
            "egress": LEDGER.summary(),
            "note": "services not listed as live return fixtures in the same shape",
        }

    return app


app = create_app()
