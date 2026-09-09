"""The canonical identity registry.

Identifiers are minted here and nowhere else. A language model never invents one, because an
identifier that a model can hallucinate is an identifier nobody can trust.

The mapping is additive: assigning a canonical identity adds a row and never alters the
CPSE's own material code. An incorrect merge is undone by deleting a cross-reference, not by
recovering overwritten data.
"""
from __future__ import annotations

import re

from sqlalchemy import select

from samepart.db.models import CanonicalMaterial

PREFIX = "SMP"
WIDTH = 6
_PAT = re.compile(rf"^{PREFIX}-(\d{{{WIDTH}}})$")


def next_id(db) -> str:
    highest = 0
    for existing in db.scalars(select(CanonicalMaterial.canonical_id)):
        m = _PAT.match(existing or "")
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{PREFIX}-{highest + 1:0{WIDTH}d}"
