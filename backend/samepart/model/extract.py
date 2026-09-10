"""Model-backed attribute extraction, for what the patterns could not read.

Called only on attributes regex left unknown, so the model handles the long tail rather than
the bulk. That keeps cost proportional to difficulty instead of to volume.

The single most important instruction in the whole system lives in this prompt: the model is
told to answer `unknown` when a value is not present, and told explicitly that guessing is
worse than abstaining. A fabricated property class on a pressure-joint bolt is a safety
problem, not a data-quality one.

Every value must come back with the exact substring that proves it. A value whose quoted
evidence does not appear in the source text is rejected before it reaches the database, so a
plausible-sounding invention cannot enter through this door.
"""
from __future__ import annotations

from dataclasses import dataclass

from samepart.dictionary.models import Family
from samepart.model.client import Model
from samepart.pipeline.extract import Value, _match_enum

SYSTEM = """You read industrial material master descriptions and extract typed attributes.

Rules, in order of importance:
1. If a value is not stated in the text, answer "unknown". Do NOT infer, assume a default,
   or use domain knowledge to fill a gap. An unknown is useful; a guess is dangerous.
2. Every value you give must be supported by an exact substring of the text. Quote it.
3. Do not convert or reformat. Report the value as the text expresses it.
4. Answer only with a JSON object. No prose.

Output shape:
{"attributes": {"<key>": {"value": "<value or unknown>", "evidence": "<exact substring>"}}}
"""


@dataclass
class ModelExtraction:
    values: dict[str, Value]
    filled: int = 0
    abstained: int = 0
    rejected: int = 0
    error: str = ""
    latency_ms: int = 0


def _describe_attribute(family: Family, key: str) -> str:
    a = family.attribute(key)
    if a is None:
        return key
    bits = [f'"{key}" ({a.label})']
    if a.type == "number":
        bits.append(f"a number in {a.unit}" if a.unit else "a number")
    if a.values:
        bits.append("one of: " + ", ".join(a.values))
    if a.value_aliases:
        pairs = list(a.value_aliases.items())[:6]
        bits.append("wordings seen in the wild: " +
                    "; ".join(f"{k} means {v}" for k, v in pairs))
    return " - ".join(bits)


def extract_missing(model: Model, family: Family, text: str,
                    current: dict[str, Value]) -> ModelExtraction:
    wanted = [k for k, v in current.items()
              if v.value is None and v.status == "unknown"
              and not (family.attribute(k) and family.attribute(k).is_derived)]
    if not wanted or not model.available:
        return ModelExtraction(values={}, error="" if wanted else "nothing missing")

    spec = "\n".join(f"- {_describe_attribute(family, k)}" for k in wanted)
    user = (f"Material family: {family.label}\n\n"
            f"Attributes to look for:\n{spec}\n\n"
            f"Text:\n\"\"\"{text}\"\"\"\n\n"
            f"Return every attribute listed, using \"unknown\" where the text does not say.")

    reply = model.json(SYSTEM, user, max_tokens=900)
    out = ModelExtraction(values={}, latency_ms=reply.latency_ms)
    if not reply.ok:
        out.error = reply.error or "model returned nothing usable"
        return out

    haystack = text.upper().replace(" ", "")
    for key, payload in (reply.data.get("attributes") or {}).items():
        if key not in wanted or not isinstance(payload, dict):
            continue
        raw = str(payload.get("value", "")).strip()
        evidence = str(payload.get("evidence", "")).strip()
        if not raw or raw.lower() in ("unknown", "none", "null", "n/a", ""):
            out.abstained += 1
            continue

        # The quoted evidence must actually be in the source. This is the guard that stops a
        # confident invention from entering the database.
        if not evidence or evidence.upper().replace(" ", "") not in haystack:
            out.rejected += 1
            continue

        attr = family.attribute(key)
        if attr and attr.type == "number":
            try:
                value: object = float(str(raw).replace(",", "").strip().rstrip("Mm"))
            except ValueError:
                out.rejected += 1
                continue
        else:
            value = _match_enum(attr, raw) if attr else raw
            if value is None:
                out.rejected += 1
                continue

        out.values[key] = Value(key, value, attr.unit if attr else None,
                                status="extracted", method="llm",
                                evidence=evidence, confidence=0.8)
        out.filled += 1
    return out
