"""Sign in to a seat."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from samepart import auth

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(description="bpcl, cpcl, iocl, ntpc or national")
    password: str


class Session(BaseModel):
    token: str
    username: str
    role: str
    org: str | None
    label: str
    actor_name: str


def _session(token: str, p: auth.Principal) -> Session:
    return Session(token=token, username=p.username, role=p.role, org=p.org,
                   label=p.label, actor_name=p.actor_name)


@router.post("/auth/login", response_model=Session)
def login(req: LoginRequest):
    token = auth.login(req.username, req.password)
    if token is None:
        # One message for both a missing user and a wrong password, so the login form does
        # not confirm which seats exist.
        raise HTTPException(401, "Wrong username or password.")
    return _session(token, auth.principal_for(req.username.lower()))


@router.get("/auth/me", response_model=Session)
def me(request: Request):
    p: auth.Principal | None = getattr(request.state, "principal", None)
    if p is None:
        raise HTTPException(401, "Not signed in.")
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    return _session(token, p)
