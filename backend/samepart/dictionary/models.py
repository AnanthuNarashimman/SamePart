"""Typed view over the YAML dictionaries.

Nothing in the pipeline hardcodes a material family. Every family, attribute, unit and
conflict gate is loaded from data at startup, which is what allows a new family to be
added without touching code.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Criticality(str, Enum):
    IDENTITY = "identity"
    CRITICAL = "critical"
    MAJOR = "major"
    INFORMATIONAL = "informational"


class GateAction(str, Enum):
    FORCE_SAME = "force_same"
    FORCE_DIFFERENT = "force_different"
    FORCE_INSUFFICIENT = "force_insufficient"
    DOWNGRADE_TO_ALTERNATIVE = "downgrade_to_alternative"


class GateWhen(str, Enum):
    ALL_PRESENT = "all_present"
    BOTH_PRESENT = "both_present"
    EITHER_MISSING = "either_missing"


class GateRule(str, Enum):
    ALL_EQUAL = "all_equal"
    ANY_NOT_EQUAL = "any_not_equal"


class AttributeDef(BaseModel):
    key: str
    label: str
    type: str
    criticality: Criticality = Criticality.INFORMATIONAL
    required_for_decision: bool | None = Field(
        None,
        description="Must this be KNOWN before a merge can be decided? Distinct from "
                    "criticality, which asks whether a DIFFERENCE means different materials. "
                    "Finish differing makes two stock items different; finish being unwritten "
                    "does not make the pair undecidable. Defaults to true for critical.",
    )
    unit: str | None = None
    dimension: str | None = None
    aliases: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    value_aliases: dict[str, str] = Field(
        default_factory=dict,
        description="Synonym seen in source text -> canonical value. Real material masters "
                    "carry many wordings for the same fact; this is where a domain owner "
                    "records them, as data.",
    )
    normalise: list[str] = Field(default_factory=list)
    derive: str | None = None

    @property
    def must_be_known(self) -> bool:
        if self.required_for_decision is not None:
            return self.required_for_decision
        return self.criticality is Criticality.CRITICAL

    @property
    def is_derived(self) -> bool:
        return self.type == "derived"


class Gate(BaseModel):
    id: str
    when: GateWhen
    attributes: list[str]
    action: GateAction
    message: str
    rule: GateRule | None = None


class SubstitutionGroup(BaseModel):
    id: str
    attribute: str
    members: list[str]
    relation: str
    condition: str


class Blocking(BaseModel):
    """How candidates are proposed for this family. Declared, not coded."""
    primary_key: list[str] = Field(default_factory=list)
    fallback: str = "canonical_text"
    fallback_top_k: int = 20


class AutoMerge(BaseModel):
    """When may the system merge without asking a person?

    Only when there is nothing to judge: every comparable attribute agrees exactly, every
    attribute that must be known is known, and no gate had to intervene. Anything short of
    that goes to a human. A sampled fraction is still sent for audit, because an automation
    rate nobody checks is a claim, not a control.
    """
    enabled: bool = False
    require_all_known: bool = True
    require_score: float = 1.0
    forbid_gate_override: bool = True
    audit_sample_rate: float = 0.05


class ClassificationAnchor(BaseModel):
    system: str = "UNSPSC"
    code: str = ""


class Naming(BaseModel):
    noun: str
    modifier: str = ""
    short_template: str = ""
    long_template: str = ""


class Family(BaseModel):
    family: str
    label: str
    version: int = 1
    naming: Naming
    blocking: Blocking = Field(default_factory=Blocking)
    classification: ClassificationAnchor = Field(default_factory=ClassificationAnchor)
    auto_merge: AutoMerge = Field(default_factory=AutoMerge)
    attributes: list[AttributeDef]
    gates: list[Gate] = Field(default_factory=list)
    substitution_groups: list[SubstitutionGroup] = Field(default_factory=list)

    def attribute(self, key: str) -> AttributeDef | None:
        return self._by_key.get(key)

    def model_post_init(self, _ctx: Any) -> None:
        object.__setattr__(self, "_by_key", {a.key: a for a in self.attributes})

    @property
    def keys_by_criticality(self) -> dict[Criticality, list[str]]:
        out: dict[Criticality, list[str]] = {c: [] for c in Criticality}
        for a in self.attributes:
            out[a.criticality].append(a.key)
        return out

    def substitution_for(self, attribute: str, a: str, b: str) -> SubstitutionGroup | None:
        """Return the group allowing a and b to be treated as related, if one exists."""
        for g in self.substitution_groups:
            if g.attribute != attribute:
                continue
            if a in g.members and b in g.members:
                return g
        return None
