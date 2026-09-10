"""Minting the Common National Material Code.

The structure is declared in `dictionaries/national_code.yaml`, not hardcoded, and it
follows the NATO Codification System precedent India already participates in: a
classification prefix plus a permanent identification number, where **the identification
number never changes even when the item is reclassified**.

That separation is the whole point. A code whose identity depends on its classification
cannot survive a reclassification, and a CPSE that has printed it on a bin label, quoted it
in a purchase order and referenced it in a maintenance plan cannot be told it has changed.
Classification is a fact about a material. Identity is the material.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import select


@dataclass(frozen=True)
class CodeFormat:
    prefix: str = "IN"
    separator: str = "-"
    classification_digits: int = 8
    serial_digits: int = 7
    check_digit: bool = True
    unclassified: str = "00000000"

    @classmethod
    def from_file(cls, path: Path) -> "CodeFormat":
        spec = yaml.safe_load(Path(path).read_text())
        f = spec.get("format", {})
        return cls(prefix=f.get("prefix", "IN"), separator=f.get("separator", "-"),
                   classification_digits=f.get("classification_digits", 8),
                   serial_digits=f.get("serial_digits", 7),
                   check_digit=f.get("check_digit", True),
                   unclassified=spec.get("unclassified_placeholder", "00000000"))

    @property
    def pattern(self) -> re.Pattern:
        s = re.escape(self.separator)
        tail = f"{s}(\\d)" if self.check_digit else ""
        return re.compile(
            rf"^{re.escape(self.prefix)}{s}(\d{{{self.classification_digits}}})"
            rf"{s}(\d{{{self.serial_digits}}}){tail}$")

    @property
    def identity_pattern(self) -> re.Pattern:
        s = re.escape(self.separator)
        tail = f"{s}(\\d)" if self.check_digit else ""
        return re.compile(
            rf"^{re.escape(self.prefix)}{s}(\d{{{self.serial_digits}}}){tail}$")


def luhn(digits: str) -> int:
    """Standard Luhn check digit. Catches every single-digit slip and most transpositions."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def compose_identity(fmt: CodeFormat, serial: int) -> str:
    """The permanent identity. This is what everything keys on, and it never changes.

    Equivalent to the NIIN inside a NATO stock number: the part that survives
    reclassification. Storing this as the primary key rather than the full code is what makes
    reclassification a metadata change instead of a migration with foreign keys to chase.
    """
    ser = str(serial).zfill(fmt.serial_digits)
    parts = [fmt.prefix, ser]
    if fmt.check_digit:
        parts.append(str(luhn(ser)))
    return fmt.separator.join(parts)


def compose_full(fmt: CodeFormat, serial: int, classification: str | None) -> str:
    """The full national code, for printing and quoting. Derived, never stored as the key."""
    cls = (classification or fmt.unclassified)[: fmt.classification_digits]
    cls = cls.rjust(fmt.classification_digits, "0")
    ser = str(serial).zfill(fmt.serial_digits)
    parts = [fmt.prefix, cls, ser]
    if fmt.check_digit:
        parts.append(str(luhn(f"{cls}{ser}")))
    return fmt.separator.join(parts)


# Kept for callers that want the printable form by default.
compose = compose_full


@dataclass
class ParsedCode:
    classification: str
    serial: int
    valid: bool
    reason: str = ""


def parse(fmt: CodeFormat, code: str) -> ParsedCode:
    """Accepts either the identity form or the full classified form."""
    text = code.strip().upper()
    m_id = fmt.identity_pattern.match(text)
    if m_id:
        ser = m_id.group(1)
        if fmt.check_digit and int(m_id.group(2)) != luhn(ser):
            return ParsedCode("", int(ser), False,
                              f"check digit is {m_id.group(2)}, expected {luhn(ser)}; "
                              f"the code was probably mistyped")
        return ParsedCode("", int(ser), True)

    m = fmt.pattern.match(text)
    if not m:
        return ParsedCode("", 0, False, "does not match the national code format")
    cls, ser = m.group(1), m.group(2)
    if fmt.check_digit:
        expected = luhn(f"{cls}{ser}")
        if int(m.group(3)) != expected:
            return ParsedCode(cls, int(ser), False,
                              f"check digit is {m.group(3)}, expected {expected}; "
                              f"the code was probably mistyped")
    return ParsedCode(cls, int(ser), True)


def reclassify(fmt: CodeFormat, code: str, new_classification: str) -> str:
    """Restate the classification and keep the identity.

    This is the rule the whole structure exists to support. The serial is carried across
    untouched, so a reclassified material is the same material with the same identity.
    """
    parsed = parse(fmt, code)
    if not parsed.valid:
        raise ValueError(f"cannot reclassify {code!r}: {parsed.reason}")
    return compose_full(fmt, parsed.serial, new_classification)


def next_serial(db) -> int:
    """Serials are never reused. The next one is always beyond the highest ever issued."""
    from samepart.db.models import CanonicalMaterial

    highest = 0
    for existing in db.scalars(select(CanonicalMaterial.canonical_id)):
        # Identity form is prefix-serial-check, so the serial is the first number.
        digits = re.findall(r"\d+", existing or "")
        if digits:
            highest = max(highest, int(digits[0]))
    return highest + 1
