"""Attribute value normalisation, driven by the `normalise` list in the dictionary."""
from __future__ import annotations

import re

_OPS = {
    "upper": lambda s: s.upper(),
    "lower": lambda s: s.lower(),
    "strip_spaces": lambda s: re.sub(r"\s+", "", s),
    "collapse_spaces": lambda s: re.sub(r"\s+", " ", s).strip(),
    "strip_non_alnum": lambda s: re.sub(r"[^A-Za-z0-9]", "", s),
    "strip_leading_zeros": lambda s: s.lstrip("0") or "0",
}


def apply_ops(value: str, ops: list[str]) -> str:
    out = value.strip()
    for op in ops:
        try:
            out = _OPS[op](out)
        except KeyError:
            raise ValueError(f"unknown normalisation op {op!r}") from None
    return out
