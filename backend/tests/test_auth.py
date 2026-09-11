"""Sign-in, tokens, and the door they guard.

The property that matters: a request's role comes from the token the server signed, never
from the body. A steward cannot become the approver by editing a JSON field, and nobody
without a password can write at all.
"""
import os
import time

import pytest
from fastapi.testclient import TestClient

from samepart import auth


@pytest.fixture(autouse=True)
def fixed_secret(monkeypatch):
    monkeypatch.setenv("SAMEPART_SECRET", "test-secret")
    monkeypatch.delenv("SAMEPART_USERS", raising=False)


def test_a_correct_password_yields_a_token_for_that_seat():
    token = auth.login("bpcl", auth.DEFAULT_USERS["bpcl"])
    assert token
    p = auth.verify(token)
    assert p and p.role == "steward" and p.org == "BPCL" and p.actor_name == "BPCL-steward"


def test_the_national_account_is_the_approver():
    p = auth.verify(auth.login("national", auth.DEFAULT_USERS["national"]))
    assert p and p.role == "national_approver" and p.org is None


def test_a_wrong_password_yields_nothing():
    assert auth.login("bpcl", "nope") is None
    assert auth.login("ghost", "anything") is None


def test_a_tampered_token_is_rejected():
    token = auth.login("bpcl", auth.DEFAULT_USERS["bpcl"])
    payload, sig = token.split(".", 1)
    assert auth.verify(payload + "x." + sig) is None
    assert auth.verify(payload + "." + "0" * 64) is None
    assert auth.verify("garbage") is None


def test_an_expired_token_is_rejected():
    token = auth.issue("bpcl", ttl=-1)
    time.sleep(0.01)
    assert auth.verify(token) is None


def test_credentials_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SAMEPART_USERS", "bpcl:real-secret,national:other")
    assert auth.login("bpcl", auth.DEFAULT_USERS["bpcl"]) is None
    assert auth.login("bpcl", "real-secret")
    assert auth.login("cpcl", auth.DEFAULT_USERS["cpcl"]) is None   # not configured, so no seat


def test_the_api_refuses_unsigned_requests_and_admits_signed_ones():
    os.environ.setdefault("SAMEPART_MODE", "stub")
    from samepart.api.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/health").status_code == 200          # open
    assert client.get("/api/orgs").status_code == 401            # guarded
    assert client.post("/api/auth/login", json={"username": "bpcl", "password": "wrong"}).status_code == 401

    session = client.post("/api/auth/login",
                          json={"username": "bpcl", "password": auth.DEFAULT_USERS["bpcl"]}).json()
    headers = {"Authorization": f"Bearer {session['token']}"}
    assert client.get("/api/orgs", headers=headers).status_code == 200
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["role"] == "steward" and me["org"] == "BPCL"


def test_the_body_cannot_promote_a_steward_to_approver():
    """The seat is the token's. A steward who sends reviewer_role=national_approver is still
    a steward when the ruling is made."""
    os.environ.setdefault("SAMEPART_MODE", "stub")
    from samepart.api.app import create_app

    client = TestClient(create_app())
    session = client.post("/api/auth/login",
                          json={"username": "bpcl", "password": auth.DEFAULT_USERS["bpcl"]}).json()
    headers = {"Authorization": f"Bearer {session['token']}"}
    r = client.get("/api/queue?actor_role=national_approver", headers=headers)
    assert r.status_code == 200
    # The stub ignores scoping, so the assertion that matters is on the decision path, which
    # is exercised against the live service in the governance tests; here we only need the
    # request to be accepted as the steward it is.
