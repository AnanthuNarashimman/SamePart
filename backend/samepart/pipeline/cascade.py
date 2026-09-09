"""The matching cascade.

Four tiers, cheapest first. Each either decides or passes down, and every decision records
which tier made it, so "why did the system say this" always has an answer.

    1. identity      same manufacturer and part number. No inference, no model call
    2. attributes    agreement over typed values. Local, instant
    3. model         only for pairs the first two could not settle          (step 4)
    4. gates         deterministic rules that can OVERRIDE any of the above

Tier 4 is not a fallback, it is a veto. It runs on every pair regardless of who decided, and
it is the reason a merge can be trusted: a domain engineer can read the gate table and know
exactly what the system will and will not merge, without reading any model output.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from samepart.dictionary.models import Criticality, Family
from samepart.gates import GateOutcome, Verdict, evaluate, values_equal
from samepart.normalise import apply_ops

WEIGHT = {
    Criticality.IDENTITY: 0.0,        # handled by tier 1, never scored
    Criticality.CRITICAL: 3.0,
    Criticality.MAJOR: 1.0,
    Criticality.INFORMATIONAL: 0.25,
}


@dataclass
class CascadeResult:
    verdict: Verdict
    decided_by: str
    score: float | None
    proposal: Verdict
    gate: GateOutcome
    rationale: str
    compared: list[str] = field(default_factory=list)
    disagreed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unobtainable: list[str] = field(default_factory=list)

    def auto_mergeable(self, policy) -> bool:
        """Nothing here is a judgement call, so nobody needs to make one."""
        if not policy.enabled or self.verdict is not Verdict.SAME:
            return False
        if policy.forbid_gate_override and self.gate.overridden:
            return False
        if policy.require_all_known and self.missing:
            return False
        if self.decided_by == "identity":
            return True
        return (self.score or 0.0) >= policy.require_score

    @property
    def gate_overrode(self) -> bool:
        return self.gate.overridden


def _norm_mpn(family: Family, value: object) -> str | None:
    if value is None:
        return None
    attr = family.attribute("manufacturer_part_number")
    ops = attr.normalise if attr else ["upper", "strip_non_alnum"]
    return apply_ops(str(value), ops)


def identity_match(family: Family, a: dict, b: dict) -> bool:
    """Same maker, same part number. The highest-precision signal in a material master."""
    ma, mb = a.get("manufacturer"), b.get("manufacturer")
    pa, pb = _norm_mpn(family, a.get("manufacturer_part_number")), _norm_mpn(family, b.get("manufacturer_part_number"))
    if not (ma and mb and pa and pb):
        return False
    return str(ma).strip().upper() == str(mb).strip().upper() and pa == pb


def attribute_agreement(family: Family, a: dict, b: dict,
                        unresolvable_a: set[str] | None = None,
                        unresolvable_b: set[str] | None = None,
                        ) -> tuple[float, list[str], list[str], list[str], list[str]]:
    """Weighted agreement over attributes present on both records.

    Returns the score, what was comparable, what disagreed, and which critical attributes
    were missing. Attributes absent from one side are NOT counted as disagreement; they are
    reported as missing, because unknown is not the same as different.
    """
    ua, ub = unresolvable_a or set(), unresolvable_b or set()
    compared: list[str] = []
    disagreed: list[str] = []
    missing_critical: list[str] = []
    unobtainable: list[str] = []
    num = den = 0.0

    for attr in family.attributes:
        w = WEIGHT[attr.criticality]
        va, vb = a.get(attr.key), b.get(attr.key)
        present = va is not None and vb is not None
        # A blank a person has already declared unanswerable is not a question any more.
        # It cannot make the records match either, so where the other side states a
        # conflict-critical fact, the two stay permanently separate rather than looping
        # back into the queue.
        gave_up = (va is None and attr.key in ua) or (vb is None and attr.key in ub)
        if gave_up:
            if attr.criticality is Criticality.CRITICAL and (va is not None or vb is not None):
                disagreed.append(attr.key)
                unobtainable.append(attr.key)
        elif attr.must_be_known and not present:
            missing_critical.append(attr.key)
        # One side states a conflict-critical fact and the other is silent. That is not
        # agreement, it is an open question: a zinc-plated bolt and a bolt whose finish was
        # never written down may or may not be the same stock item, and only a person can
        # say. Both sides silent is fine; neither record claims anything.
        elif (attr.criticality is Criticality.CRITICAL
              and (va is None) != (vb is None)):
            missing_critical.append(attr.key)
        if not w or not present:
            continue
        compared.append(attr.key)
        den += w
        if values_equal(family, attr.key, va, vb):
            num += w
        else:
            disagreed.append(attr.key)

    return (num / den if den else 0.0), compared, disagreed, missing_critical, unobtainable


def run(family: Family, a: dict, b: dict,
        unresolvable_a: set[str] | None = None,
        unresolvable_b: set[str] | None = None) -> CascadeResult:
    settled = (unresolvable_a or set()) | (unresolvable_b or set())
    if identity_match(family, a, b):
        gate = evaluate(family, a, b, Verdict.SAME, settled)
        return CascadeResult(
            verdict=gate.verdict, decided_by="identity", score=1.0,
            proposal=Verdict.SAME, gate=gate,
            rationale="Same manufacturer and part number. Identity established without inference.",
        )

    score, compared, disagreed, missing, unobtainable = attribute_agreement(
        family, a, b, unresolvable_a, unresolvable_b)

    if disagreed:
        proposal = Verdict.DIFFERENT
        why = (f"{len(disagreed)} of {len(compared)} comparable attributes disagree."
               if compared else
               f"Cannot be reconciled on {', '.join(disagreed)}: the value is recorded as "
               f"unobtainable on one side.")
    elif missing:
        proposal = Verdict.INSUFFICIENT_EVIDENCE
        why = f"Critical attribute unknown on at least one record: {', '.join(missing)}."
    elif score >= 0.999:
        proposal = Verdict.SAME
        why = f"All {len(compared)} comparable attributes agree."
    else:
        proposal = Verdict.INSUFFICIENT_EVIDENCE
        why = "Attribute evidence is too thin to decide."

    gate = evaluate(family, a, b, proposal, settled)
    verdict = gate.verdict

    # A value that has been established as unobtainable ends the question. It must not be
    # softened back into a substitution proposal by a later gate, or the escape hatch simply
    # moves work from one queue to another.
    if unobtainable and verdict in (Verdict.SAME, Verdict.POSSIBLE_ALTERNATIVE):
        verdict = Verdict.DIFFERENT
        why = (f"{', '.join(unobtainable)} is recorded as unobtainable on one record, so "
               f"sameness can never be established. Kept as separate identities.")

    decided_by = "gate" if gate.overridden else "attributes"
    rationale = why if not gate.overridden else f"{why} {gate.rationale}"
    return CascadeResult(verdict=verdict, decided_by=decided_by, score=round(score, 4),
                         proposal=proposal, gate=gate, rationale=rationale.strip(),
                         compared=compared, disagreed=disagreed, missing=missing,
                         unobtainable=unobtainable)
