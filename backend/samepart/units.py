"""Unit normalisation.

The problem statement names units of measurement as one of the axes on which the same
material diverges across organisations. One CPSE issues a bolt as EA, another as a box of
100, a third by weight. Prices and demand cannot be compared until every quantity is
expressed in the same base unit, so normalisation happens once at ingestion and everything
downstream reasons in base units only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


class UnknownUnitError(ValueError):
    pass


class IncompatibleUnitsError(ValueError):
    pass


@dataclass(frozen=True)
class UnitSpec:
    code: str
    dimension: str
    factor: float
    base: str


def _norm(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


class UnitRegistry:
    def __init__(self, spec: dict) -> None:
        # Unit codes are matched case-sensitively and take priority; aliases are matched
        # case-insensitively. Both indexes are needed because real registries contain
        # genuine case-only collisions, such as m for metre against M for per-thousand.
        self._by_code: dict[str, UnitSpec] = {}
        self._by_alias: dict[str, UnitSpec] = {}
        self._bases: dict[str, str] = {}
        self.cross_dimension = spec.get("cross_dimension", [])

        for dimension, block in spec["dimensions"].items():
            base = block["base"]
            self._bases[dimension] = base
            for code, cfg in block["units"].items():
                unit = UnitSpec(code=code, dimension=dimension,
                               factor=float(cfg["factor"]), base=base)
                if code in self._by_code:
                    raise ValueError(f"duplicate unit code {code!r}")
                self._by_code[code] = unit

                for alias in cfg.get("aliases", []):
                    key = _norm(str(alias))
                    existing = self._by_alias.get(key)
                    if existing is not None and existing.code != code:
                        raise ValueError(
                            f"unit alias {alias!r} is claimed by both "
                            f"{existing.code} and {code}"
                        )
                    self._by_alias[key] = unit

    @classmethod
    def from_file(cls, path: Path) -> "UnitRegistry":
        return cls(yaml.safe_load(Path(path).read_text()))

    def base_of(self, dimension: str) -> str:
        return self._bases[dimension]

    def resolve(self, token: str) -> UnitSpec:
        unit = self.try_resolve(token)
        if unit is None:
            raise UnknownUnitError(f"unrecognised unit {token!r}")
        return unit

    def try_resolve(self, token: str) -> UnitSpec | None:
        exact = token.strip()
        if exact in self._by_code:
            return self._by_code[exact]
        key = _norm(token)
        if key in self._by_alias:
            return self._by_alias[key]
        # Last resort: a case-insensitive code match, which is safe only when exactly one
        # code matches. This is what keeps "kg" and "KG" working without letting "m"
        # silently resolve to the per-thousand packaging code.
        hits = [u for c, u in self._by_code.items() if c.lower() == key]
        return hits[0] if len(hits) == 1 else None

    def to_base(self, value: float, unit: str) -> tuple[float, str]:
        """Express a quantity in its dimension's base unit."""
        spec = self.resolve(unit)
        return value * spec.factor, spec.base

    def convert(self, value: float, frm: str, to: str) -> float:
        a, b = self.resolve(frm), self.resolve(to)
        if a.dimension != b.dimension:
            raise IncompatibleUnitsError(
                f"cannot convert {a.code} ({a.dimension}) to {b.code} ({b.dimension}) "
                f"without a material property; see cross_dimension in units.yaml"
            )
        return value * a.factor / b.factor

    def unit_price_in_base(self, price: float, quantity: float, unit: str) -> float:
        """Price per base unit, which is the only comparable form across organisations.

        A price of 450 for one BOX-100 and a price of 5.10 for one EA are not comparable
        as written; they are 4.50 and 5.10 per each once normalised.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        base_qty, _ = self.to_base(quantity, unit)
        return price / base_qty
