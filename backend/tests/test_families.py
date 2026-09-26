"""Adding a family at runtime: persisted, governed, validated, audited.

The endpoint existed as a demo trick that held the family in memory until the next restart.
These pin down what makes it a feature: the file is still there after a reload, only the
approver may do it, a name clash is refused unless replacement is explicit, a bad file is
explained rather than crashed on, and the audit chain records the act.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from samepart import auth
from samepart.config import settings
from samepart.db.models import Base, DecisionEvent
from samepart.dictionary.loader import load_dictionary


MINIMAL = """
family: flange_test
label: Flange, test
naming:
  noun: FLANGE
  short_template: "{noun}; {nominal_size_mm}NB"
attributes:
  - key: nominal_size_mm
    label: Nominal bore
    type: number
    unit: mm
    dimension: length
    criticality: critical
    patterns: ['(?P<value>\\\\d+)\\\\s?NB']
blocking:
  primary_key: [nominal_size_mm]
"""


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SAMEPART_SECRET", "test-secret")
    monkeypatch.delenv("SAMEPART_USERS", raising=False)
    monkeypatch.setenv("SAMEPART_MODE", "live")
    # The families directory and the database both go to tmp; the built-in dictionaries stay.
    object.__setattr__(settings, "families_dir", tmp_path / "families")
    from samepart.db import session as db_session
    engine = create_engine(f"sqlite:///{tmp_path / 'samepart.db'}", future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "_engine", engine)
    monkeypatch.setattr(db_session, "_Factory", None)
    from samepart.api import deps
    deps.dictionary.cache_clear()
    yield
    deps.dictionary.cache_clear()


def client_as(username: str):
    from samepart.api.app import create_app
    c = TestClient(create_app())
    session = c.post("/api/auth/login",
                     json={"username": username, "password": auth.DEFAULT_USERS[username]}).json()
    c.headers["Authorization"] = f"Bearer {session['token']}"
    return c


def test_the_approver_adds_a_family_and_it_survives_a_reload(tmp_path):
    c = client_as("national")
    r = c.post("/api/families", content=MINIMAL, headers={"content-type": "text/plain"})
    assert r.status_code == 201, r.text
    assert r.json()["family"] == "flange_test" and r.json()["replaced"] is False

    names = {f["family"]: f for f in c.get("/api/families").json()}
    assert names["flange_test"]["added"] is True
    assert names["hex_bolt"]["added"] is False

    # A fresh load from disk, as a restart would do, still has it.
    d = load_dictionary(settings.dictionary_dir, settings.families_dir)
    assert "flange_test" in d.families and "flange_test" in d.added


def test_a_steward_may_not_add_a_family():
    c = client_as("bpcl")
    r = c.post("/api/families", content=MINIMAL, headers={"content-type": "text/plain"})
    assert r.status_code == 403


def test_a_name_clash_is_refused_unless_replacement_is_explicit():
    c = client_as("national")
    assert c.post("/api/families", content=MINIMAL, headers={"content-type": "text/plain"}).status_code == 201
    again = c.post("/api/families", content=MINIMAL, headers={"content-type": "text/plain"})
    assert again.status_code == 409
    replaced = c.post("/api/families?replace=true", content=MINIMAL, headers={"content-type": "text/plain"})
    assert replaced.status_code == 201 and replaced.json()["replaced"] is True


def test_a_bad_file_is_explained_not_crashed_on():
    c = client_as("national")
    bad_unit = MINIMAL.replace("unit: mm", "unit: furlongs")
    r = c.post("/api/families", content=bad_unit, headers={"content-type": "text/plain"})
    assert r.status_code == 422 and "furlongs" in r.json()["detail"]

    not_yaml = "family: [unclosed"
    r = c.post("/api/families", content=not_yaml, headers={"content-type": "text/plain"})
    assert r.status_code == 422 and "YAML" in r.json()["detail"]

    missing = "family: x\nlabel: y\n"
    r = c.post("/api/families", content=missing, headers={"content-type": "text/plain"})
    assert r.status_code == 422 and "attributes" in r.json()["detail"]


def test_adding_a_family_is_an_audited_act():
    c = client_as("national")
    c.post("/api/families", content=MINIMAL, headers={"content-type": "text/plain"})
    from samepart.db.session import session_scope
    with session_scope() as db:
        events = db.execute(select(DecisionEvent)).scalars().all()
    assert [e.action for e in events] == ["family_loaded"]
    assert events[0].actor == "national-approver"
    assert events[0].payload["family"] == "flange_test"
    assert events[0].entry_hash                 # sealed into the chain like any decision


def test_an_existing_family_can_be_fetched_as_a_starting_point():
    c = client_as("bpcl")
    r = c.get("/api/families/hex_bolt/yaml")
    assert r.status_code == 200 and r.text.startswith("#") and "family: hex_bolt" in r.text
    assert c.get("/api/families/nope/yaml").status_code == 404
