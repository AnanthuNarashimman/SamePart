"""The canonical identity registry.

Identifiers are minted here and nowhere else. A language model never invents one, because an
identifier a model can hallucinate is an identifier nobody can trust.

What is stored is the **permanent identity**, following the rule India's own codification
bureau already applies: the identification number survives reclassification. The printable
national code, which carries the classification prefix, is derived on the way out.

The mapping is additive. Assigning a canonical identity adds a row and never alters the
CPSE's own material code, so an incorrect merge is undone by deleting a cross-reference
rather than by recovering overwritten data.
"""
from __future__ import annotations

from functools import lru_cache

from samepart.config import settings
from samepart.pipeline.national_code import (CodeFormat, compose_full, compose_identity,
                                             next_serial, parse)


@lru_cache(maxsize=1)
def code_format() -> CodeFormat:
    return CodeFormat.from_file(settings.dictionary_dir / "national_code.yaml")


def next_id(db) -> str:
    """Mint the next permanent identity. Serials are never reused."""
    return compose_identity(code_format(), next_serial(db))


def national_code(identity: str, classification: str | None) -> str:
    """The printable Common National Material Code for a stored identity."""
    fmt = code_format()
    parsed = parse(fmt, identity)
    if not parsed.valid:
        return identity
    return compose_full(fmt, parsed.serial, classification)
