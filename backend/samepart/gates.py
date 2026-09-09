"""Deterministic conflict gates.

These run after whichever tier of the cascade produced a verdict and can override it.
They are never a model call. The whole point is that a domain engineer can read the gate
table in the dictionary, check it against their own specification knowledge, and know
exactly what the system will and will not merge.

Precedence, chosen so that the dangerous error is the one the system refuses to make:
a contradiction between identity evidence and a critical-specification conflict resolves
to "insufficient evidence", never to a merge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from samepart.dictionary.models import Family, GateAction, GateWhen, GateRule


class Verdict(str, Enum):
    SAME = "same_material"
    POSSIBLE_ALTERNATIVE = "possible_alternative"
    DIFFERENT = "different"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class GateFiring:
    gate_id: str
    action: GateAction
    message: str
    attributes: list[str]
    detail: str = ""


@dataclass
class GateOutcome:
    verdict: Verdict
    overridden: bool
    firings: list[GateFiring] = field(default_factory=list)
    substitution_conditions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def rationale(self) -> str:
        if not self.firings:
            return "No gate fired; the verdict from the matching tier stands."
        return " ".join(f.message for f in self.firings)


Attrs = dict[str, object]


def _present(attrs: Attrs, key: str) -> bool:
    value = attrs.get(key)
    return value is not None and str(value).strip() != "" and str(value).lower() != "unknown"


def values_equal(family: Family, key: str, a: object, b: object) -> bool:
    """Equality that respects declared equivalences.

    ISO 4014 and DIN 931 are different strings naming the same specification. Treating
    them as a conflict would produce a false rejection, which is a quieter failure than a
    false merge but still a failure.
    """
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    sa, sb = str(a).strip(), str(b).strip()
    if sa == sb:
        return True
    group = family.substitution_for(key, sa, sb)
    return bool(group and group.relation == "equivalent")


def _conflicts(family: Family, a: Attrs, b: Attrs, keys: list[str]) -> list[str]:
    return [
        k for k in keys
        if _present(a, k) and _present(b, k) and not values_equal(family, k, a[k], b[k])
    ]


def evaluate(
    family: Family,
    a: Attrs,
    b: Attrs,
    incoming: Verdict = Verdict.INSUFFICIENT_EVIDENCE,
) -> GateOutcome:
    """Apply the family's gate table to a candidate pair."""
    firings: list[GateFiring] = []
    conditions: list[str] = []
    notes: list[str] = []

    for gate in family.gates:
        keys = gate.attributes

        if gate.when is GateWhen.EITHER_MISSING:
            missing = [k for k in keys if not (_present(a, k) and _present(b, k))]
            if missing:
                firings.append(GateFiring(gate.id, gate.action, gate.message, missing,
                                          detail=f"unknown on at least one record: {', '.join(missing)}"))
            continue

        if gate.when is GateWhen.ALL_PRESENT:
            if not all(_present(a, k) and _present(b, k) for k in keys):
                continue
            if gate.rule is GateRule.ALL_EQUAL:
                if all(values_equal(family, k, a[k], b[k]) for k in keys):
                    firings.append(GateFiring(gate.id, gate.action, gate.message, list(keys)))
            continue

        if gate.when is GateWhen.BOTH_PRESENT:
            conflicting = _conflicts(family, a, b, keys)
            if not conflicting:
                continue

            # A declared substitution turns a hard conflict into a conditional alternative,
            # and carries the condition under which the substitution actually holds.
            softened = []
            for k in list(conflicting):
                group = family.substitution_for(k, str(a[k]), str(b[k]))
                if group and group.relation == "possible_alternative":
                    conditions.append(group.condition.strip())
                    softened.append(k)
                    conflicting.remove(k)

            if softened:
                firings.append(GateFiring(
                    "substitution_rule", GateAction.DOWNGRADE_TO_ALTERNATIVE,
                    "A declared substitution covers this difference; identities stay separate.",
                    softened,
                    detail="; ".join(f"{k}: {a[k]} vs {b[k]}" for k in softened),
                ))

            if conflicting:
                firings.append(GateFiring(
                    gate.id, gate.action, gate.message, conflicting,
                    detail="; ".join(f"{k}: {a[k]} vs {b[k]}" for k in conflicting),
                ))

    verdict, notes = _resolve(incoming, firings)
    return GateOutcome(
        verdict=verdict,
        overridden=verdict != incoming,
        firings=firings,
        substitution_conditions=list(dict.fromkeys(conditions)),
        notes=notes,
    )


def _resolve(incoming: Verdict, firings: list[GateFiring]) -> tuple[Verdict, list[str]]:
    actions = {f.action for f in firings}
    notes: list[str] = []

    same = GateAction.FORCE_SAME in actions
    diff = GateAction.FORCE_DIFFERENT in actions
    insuf = GateAction.FORCE_INSUFFICIENT in actions
    down = GateAction.DOWNGRADE_TO_ALTERNATIVE in actions

    if same and diff:
        notes.append(
            "Identity evidence and a critical specification conflict disagree. One of the "
            "two records is very likely mis-described. Routed for human resolution rather "
            "than merged or split automatically."
        )
        return Verdict.INSUFFICIENT_EVIDENCE, notes

    if diff:
        return Verdict.DIFFERENT, notes
    if same:
        if down:
            notes.append("Identity matched, so the substitution note is informational only.")
        return Verdict.SAME, notes
    if insuf:
        return Verdict.INSUFFICIENT_EVIDENCE, notes
    if down:
        if incoming is Verdict.SAME:
            return Verdict.POSSIBLE_ALTERNATIVE, notes
        if incoming is Verdict.DIFFERENT:
            return Verdict.POSSIBLE_ALTERNATIVE, notes
        return incoming, notes

    return incoming, notes
