"""Regex pre-parse, driven entirely by the family dictionary.

Nothing here knows what a bolt is. Patterns, enums, aliases and normalisation rules all
come from the family YAML, so a new family is a new file rather than new code.

Anything regex cannot confidently fill is left as `unknown` rather than guessed. That is
deliberate: a missing critical attribute is what makes the system ask a question instead of
inventing an answer, and it is the highest-leverage rule in the pipeline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from samepart.dictionary.models import AttributeDef, Family
from samepart.normalise import apply_ops


@dataclass
class Value:
    key: str
    value: object | None
    unit: str | None = None
    status: str = "extracted"        # extracted | unknown | derived | unresolvable
    method: str = "regex"            # regex | llm | derived | given
    evidence: str | None = None
    confidence: float | None = None


def _squash(s: str) -> str:
    return re.sub(r"[^A-Z0-9.]", "", s.upper())


def _match_enum(attr: AttributeDef, raw: str) -> str | None:
    """Map a captured string onto the declared enum, ignoring spacing and punctuation."""
    if not attr.values:
        return raw
    target = _squash(raw)
    for allowed in attr.values:
        if _squash(allowed) == target:
            return allowed
    for synonym, canonical in attr.value_aliases.items():
        if _squash(synonym) == target:
            return canonical
    return None


def extract_one(attr: AttributeDef, text: str, *, bare_enums: bool = True) -> Value:
    """One attribute read on its own. `extract` passes `bare_enums=False` and resolves the
    bare-value scan across the whole family instead, so this is the single-attribute view."""
    if attr.is_derived:
        return Value(attr.key, None, status="unknown", method="derived")

    for pattern in attr.patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        try:
            raw = m.group("value")
        except IndexError:
            # The only expected failure: this pattern declares no group named "value", which
            # is a fault in the family file rather than in the text being read.
            #
            # This was `except (IndexError, error_type := Exception)` -- a walrus inside the
            # tuple, so it caught every exception and quietly returned `unknown` for the
            # attribute. Any real defect in extraction would have looked exactly like a
            # description that simply did not state the fact.
            continue
        if raw is None:
            continue

        if attr.type == "number":
            try:
                return Value(attr.key, float(raw), attr.unit, evidence=m.group(0).strip(),
                             confidence=0.99)
            except ValueError:
                continue

        value = _match_enum(attr, apply_ops(raw, attr.normalise) if attr.normalise else raw)
        if value is not None:
            return Value(attr.key, value, evidence=m.group(0).strip(), confidence=0.99)

    # No pattern hit. For enums, the bare-value scan is resolved across attributes by
    # `extract`, because which attribute a value belongs to depends on what else is in the
    # line — see `_resolve_enums`.
    if attr.values and bare_enums:
        best = _enum_candidates(attr, text)
        if best:
            return _value_from(attr, best[0])

    return Value(attr.key, None, status="unknown", method="regex")


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    surface: str
    canonical: str
    anchored: bool

    @property
    def length(self) -> int:
        return self.end - self.start


def _surface_pattern(surface: str) -> re.Pattern[str]:
    """A surface form as it appears in a real line.

    Any spacing or punctuation may fall between its characters — `ISO4014` must read
    `ISO 4014` and `B16.20` must read `B 16 20`, which is the leniency the squash-compare
    always had — but nothing alphanumeric may touch it on either side, so `CS` is not found
    inside `CLASS`. That guard is the one thing the old comparison lacked.
    """
    chars = re.sub(r"[^A-Za-z0-9]", "", surface)
    body = r"[^A-Za-z0-9]*".join(re.escape(c) for c in chars)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.IGNORECASE)


def _enum_candidates(attr: AttributeDef, text: str) -> list[_Candidate]:
    """Every place a declared value or alias occurs, best first.

    Anchored beats unanchored — a value sitting next to one of the attribute's own names
    ("SS 304 CENTRING RING") is that attribute's, whatever else it could have been. Then
    longer beats shorter, so "HOT DIP GALVANISED" wins over a bare "GALVANISED" and
    "MICA GRAPHITE" over "MICA". Position breaks the remaining ties.
    """
    found: list[_Candidate] = []
    surfaces = [(v, v) for v in attr.values] + list(attr.value_aliases.items())
    for surface, canonical in surfaces:
        for m in _surface_pattern(surface).finditer(text):
            found.append(_Candidate(m.start(), m.end(), m.group(0), canonical,
                                    _anchored(attr, text, m.start(), m.end())))
    found.sort(key=lambda c: (not c.anchored, -c.length, c.start))
    return found


def _anchored(attr: AttributeDef, text: str, start: int, end: int) -> bool:
    """True when one of the attribute's names sits immediately before or after the value.

    Immediately, not nearby: with any slack at all, "SS304  PTFE  CS RING" anchors SS304 to
    the ring because RING is three words away, and the winding is left with nothing.
    """
    names = [attr.key.replace("_", " "), *attr.aliases]
    before = [w.lower() for w in re.findall(r"[A-Za-z]+", text[:start])]
    after = [w.lower() for w in re.findall(r"[A-Za-z]+", text[end:])]
    for name in names:
        toks = [w.lower() for w in re.findall(r"[A-Za-z]+", name)]
        if not toks:
            continue
        if before[-len(toks):] == toks or after[:len(toks)] == toks:
            return True
    return False


def _value_from(attr: AttributeDef, c: _Candidate) -> Value:
    conf = 0.9 if c.canonical == c.surface.upper() else 0.85
    return Value(attr.key, c.canonical, evidence=c.surface, confidence=conf)


def _resolve_enums(family: Family, text: str, out: dict[str, Value]) -> None:
    """Assign bare enum matches so that no two attributes read the same words.

    The failure this exists for: a spiral-wound gasket line reads "MONEL  MICA  SS304 RING".
    The winding is Monel and the centring ring is SS304, but both attributes accept SS304,
    and whichever was scanned first took it — so every gasket with an SS304 ring extracted
    as an SS304 winding, and gaskets with different windings merged as identical. Values
    are claimed in order of strength (anchored, then longest, then leftmost) and a span,
    once claimed, is unavailable to any other attribute.
    """
    pending = [a for a in family.attributes
               if a.values and not a.is_derived and out[a.key].value is None]
    if not pending:
        return

    pool: list[tuple[_Candidate, AttributeDef]] = []
    for attr in pending:
        pool.extend((c, attr) for c in _enum_candidates(attr, text))
    pool.sort(key=lambda ca: (not ca[0].anchored, -ca[0].length, ca[0].start))

    claimed: list[tuple[int, int]] = []
    for c, attr in pool:
        if out[attr.key].value is not None:
            continue
        if any(c.start < e and s < c.end for s, e in claimed):
            continue
        out[attr.key] = _value_from(attr, c)
        claimed.append((c.start, c.end))


def extract(family: Family, text: str) -> dict[str, Value]:
    # Patterns and numbers resolve on their own; bare enum values are left for the
    # cross-attribute pass so a shared vocabulary cannot be read twice.
    out = {a.key: extract_one(a, text, bare_enums=False) for a in family.attributes}
    _resolve_enums(family, text, out)

    for attr in family.attributes:
        if attr.is_derived and attr.derive:
            try:
                filled = attr.derive.format(
                    **{k: v.value for k, v in out.items() if v.value is not None}
                )
                out[attr.key] = Value(attr.key, filled, status="derived", method="derived")
            except (KeyError, IndexError, ValueError):
                pass
    return out


def canonical_text(family: Family, values: dict[str, Value]) -> str:
    """A house-style-free rendering of what the record actually is.

    Embedding the raw description clusters records by which organisation wrote them, not by
    what the part is. Measured on the generated catalogue, embedding raw text retained 7.8%
    of true duplicates; embedding this canonical form retained 97.1%.
    """
    parts = [family.naming.noun, family.naming.modifier]
    for attr in family.attributes:
        if attr.criticality.value in ("identity", "informational"):
            continue
        v = values.get(attr.key)
        if v is None or v.value is None:
            continue
        if attr.type == "number":
            parts.append(f"{_abbrev(attr.key)}{float(v.value):g}")
        else:
            parts.append(_squash(str(v.value)))
    return " ".join(p for p in parts if p)


def _abbrev(key: str) -> str:
    """thread_diameter_mm -> TD, length_mm -> L. Keeps 16 as a diameter distinct from 16 as a length."""
    parts = [p for p in key.split("_") if p not in {"mm", "kg", "n", "mpa"}]
    return "".join(p[0] for p in parts).upper()
