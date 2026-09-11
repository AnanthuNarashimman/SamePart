"""Who may do what.

The interesting rule is the two-tier one, and it exists for a political reason rather than a
technical one. A CPSE will accept its own steward deciding about its own codes. It will not
accept another organisation's steward deciding that its code and someone else's are the same
thing. So a relationship confined to one organisation is a local decision, and one that spans
organisations is the moment a national identifier comes into existence and needs an authority
both sides recognise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from samepart.config import settings


@dataclass(frozen=True)
class Role:
    key: str
    label: str
    description: str
    permissions: frozenset[str]
    scope: str = "all"


@dataclass
class Governance:
    roles: dict[str, Role] = field(default_factory=dict)
    default_state: str = "review_everything"
    policy_change_role: str = "administrator"

    def role(self, key: str) -> Role | None:
        return self.roles.get(key)

    def may(self, role_key: str, permission: str) -> bool:
        role = self.roles.get(role_key)
        return bool(role and permission in role.permissions)


@lru_cache(maxsize=1)
def load(path: Path | None = None) -> Governance:
    spec = yaml.safe_load((path or settings.dictionary_dir / "governance.yaml").read_text())
    roles = {
        key: Role(key=key, label=cfg.get("label", key),
                  description=" ".join(str(cfg.get("description", "")).split()),
                  permissions=frozenset(cfg.get("permissions", [])),
                  scope=cfg.get("scope", "all"))
        for key, cfg in spec.get("roles", {}).items()
    }
    control = spec.get("policy_control", {})
    return Governance(roles=roles,
                      default_state=control.get("default_state", "review_everything"),
                      policy_change_role=control.get("change_requires", "administrator"))


@dataclass
class Ruling:
    allowed: bool
    reason: str = ""
    required_role: str = ""


def may_decide(role_key: str, orgs_involved: set[str], reviewer_org: str | None = None) -> Ruling:
    """May this person settle a relationship between these records?"""
    gov = load()
    role = gov.role(role_key)
    if role is None:
        return Ruling(False, f"unknown role {role_key!r}")

    cross = len(orgs_involved) > 1
    if cross:
        if "decide_cross_org" in role.permissions:
            return Ruling(True)
        return Ruling(
            False,
            "This pair spans "
            f"{', '.join(sorted(orgs_involved))}. Approving it creates a national identifier, "
            "which is not a decision one organisation makes about another's codes.",
            required_role="national_approver")

    if "decide_within_org" not in role.permissions:
        return Ruling(False, f"{role.label} may not approve mappings",
                      required_role="steward")

    if role.scope == "own_organisation" and reviewer_org and orgs_involved:
        if reviewer_org not in orgs_involved:
            return Ruling(
                False,
                f"{role.label} for {reviewer_org} cannot decide about "
                f"{', '.join(sorted(orgs_involved))}'s codes.",
                required_role="steward")
    return Ruling(True)


def may_answer(role_key: str, record_org: str, reviewer_org: str | None = None) -> Ruling:
    """May this person state a fact about this record, or declare it unknowable?

    Answering is not approving and creates no identifier, so it is open to any role with the
    permission — but a steward speaks only for their own organisation's records. Nobody else
    knows what BPCL meant by a blank on a BPCL code.
    """
    gov = load()
    role = gov.role(role_key)
    if role is None:
        return Ruling(False, f"unknown role {role_key!r}")
    if "answer" not in role.permissions:
        return Ruling(False, f"{role.label} may not answer questions", required_role="steward")
    if role.scope == "own_organisation" and reviewer_org and reviewer_org != record_org:
        return Ruling(
            False,
            f"{role.label} for {reviewer_org} cannot answer for a {record_org} record; only "
            f"{record_org} knows what its own description meant.",
            required_role="steward")
    return Ruling(True)


def actor_name(role_key: str, reviewer_org: str | None) -> str:
    """The name that goes on the audit event: which organisation, in which role."""
    if role_key == "steward" and reviewer_org:
        return f"{reviewer_org}-steward"
    return role_key.replace("_", "-")
