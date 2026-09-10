"""Model-backed pairwise comparison, for pairs the rules cannot settle.

The model is given **typed attributes with their evidence**, never the raw descriptions. It
is comparing established facts, not guessing at similar-looking strings, and that is what
makes its answer reviewable.

Three constraints, all deliberate.

1. **It cannot invent a merge.** A verdict of same is a recommendation. Model-decided pairs
   are never auto-merged, no matter what the automation policy says, because the policy
   permits automation only where nothing is being judged.
2. **The gates still run afterwards** and can overrule it. A model that says same over a
   grade conflict is overruled by a rule a domain engineer can read.
3. **It must name the deciding attribute.** A verdict with no attribute behind it is
   rejected, because "they look alike" is exactly the reasoning this system exists to
   replace.

Where the model earns its place is the case the dictionary has no rule for. Those verdicts
are also the raw material for new rules: a substitution the model keeps proposing is a
substitution a domain owner should consider writing down.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from samepart.dictionary.models import Family
from samepart.gates import Verdict
from samepart.model.client import Model

SYSTEM = """You compare two industrial materials and decide whether they are the same item.

You are given extracted attributes, not free text. Reason only from those attributes.

Answer with exactly one verdict:
- "same_material": every identifying attribute agrees. The same physical item.
- "possible_alternative": different items that could substitute in some applications. Say
  in "condition" exactly when the substitution is safe and when it is not.
- "different": a real specification difference makes these different items.
- "insufficient_evidence": you cannot tell from what you were given. This is a good answer.
  Prefer it to a guess.

Each attribute carries two separate properties. Do not conflate them.
- "identity-bearing": if the two records give DIFFERENT values, they are different items.
- "must be known": the value has to be present on both records before anything can be
  decided at all.

An attribute can be identity-bearing without needing to be known. A finish that differs means
a different stock item; a finish nobody wrote down does NOT make the pair undecidable,
because neither record is claiming anything about it.

Rules:
1. Never treat an unknown as agreement, but never treat it as disagreement either. If an
   attribute is unknown on one side and is NOT marked "must be known", ignore it and judge
   on what is stated.
2. Answer insufficient_evidence only when an attribute marked "must be known" is missing, or
   when what is stated genuinely does not settle the question.
3. Name the single attribute that drove your decision in "deciding_attribute".
4. Safety first. If a wrong merge could put the wrong part into service, say different or
   insufficient_evidence.
5. Answer only with a JSON object. No prose.

Output shape:
{"verdict": "...", "deciding_attribute": "...", "reason": "one sentence",
 "condition": "when substitution is safe, only for possible_alternative"}
"""

_ALLOWED = {v.value for v in Verdict}


@dataclass
class ModelVerdict:
    verdict: Verdict | None
    deciding_attribute: str = ""
    reason: str = ""
    condition: str = ""
    ok: bool = False
    error: str = ""
    latency_ms: int = 0
    tokens: int = 0
    notes: list[str] = field(default_factory=list)


def _render(family: Family, attrs: dict, label: str) -> str:
    lines = [f"{label}:"]
    for a in family.attributes:
        if a.is_derived:
            continue
        value = attrs.get(a.key)
        shown = "unknown" if value is None else value
        flags = []
        if a.criticality.value in ("critical", "identity"):
            flags.append("identity-bearing")
        if a.must_be_known:
            flags.append("must be known")
        if not flags:
            flags.append("informational")
        lines.append(f"  {a.key} [{', '.join(flags)}]: {shown}")
    return "\n".join(lines)


def compare(model: Model, family: Family, a: dict, b: dict) -> ModelVerdict:
    if not model.available:
        return ModelVerdict(None, error="no model configured")

    # The family's declared substitutions are domain knowledge the model has no way to
    # infer. Without them it calls a known-interchangeable pair "different", and the gate
    # has to correct it afterwards, which wastes the call and muddies the audit trail.
    subs = ""
    if family.substitution_groups:
        lines = []
        for g in family.substitution_groups:
            lines.append(f"  - {g.attribute}: {' and '.join(g.members)} are "
                         f"{g.relation.replace('_', ' ')}. {g.condition.strip()}")
        subs = ("\n\nDeclared substitutions for this family, which are approved domain "
                "knowledge:\n" + "\n".join(lines))

    user = (f"Material family: {family.label}\n\n"
            f"{_render(family, a, 'Record A')}\n\n{_render(family, b, 'Record B')}\n\n"
            f"{subs}\n\nAre these the same item?")

    reply = model.json(SYSTEM, user, max_tokens=600)
    out = ModelVerdict(None, latency_ms=reply.latency_ms,
                       tokens=reply.tokens_in + reply.tokens_out)
    if not reply.ok:
        out.error = reply.error or "model returned nothing usable"
        return out

    raw = str(reply.data.get("verdict", "")).strip().lower()
    if raw not in _ALLOWED:
        out.error = f"model returned an unrecognised verdict {raw!r}"
        return out

    deciding = str(reply.data.get("deciding_attribute", "")).strip()
    known = {x.key for x in family.attributes}
    # A verdict that separates records must name the attribute that separates them; "they
    # look alike" is the reasoning this system exists to replace. A verdict of same has
    # nothing to name, because nothing disagreed.
    needs_attribute = raw in (Verdict.DIFFERENT.value, Verdict.POSSIBLE_ALTERNATIVE.value)
    if needs_attribute and deciding not in known:
        out.error = (f"verdict {raw!r} cited no known attribute "
                     f"(gave {deciding!r}); rejected")
        return out
    if deciding not in known:
        deciding = ""

    out.verdict = Verdict(raw)
    out.deciding_attribute = deciding
    out.reason = str(reply.data.get("reason", "")).strip()[:400]
    out.condition = str(reply.data.get("condition", "")).strip()[:600]
    out.ok = True
    return out
