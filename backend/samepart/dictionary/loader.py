"""Loads the YAML dictionaries into typed objects at startup."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from samepart.dictionary.models import Family
from samepart.units import UnitRegistry


@dataclass
class Dictionary:
    units: UnitRegistry
    families: dict[str, Family]

    def family(self, name: str) -> Family:
        try:
            return self.families[name]
        except KeyError:
            known = ", ".join(sorted(self.families)) or "none"
            raise KeyError(f"unknown family {name!r}; loaded families: {known}") from None

    @property
    def family_names(self) -> list[str]:
        return sorted(self.families)


def load_dictionary(root: Path) -> Dictionary:
    root = Path(root)
    units = UnitRegistry.from_file(root / "units.yaml")

    families: dict[str, Family] = {}
    family_dir = root / "families"
    for path in sorted(family_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        fam = Family.model_validate(raw)
        if fam.family in families:
            raise ValueError(f"duplicate family {fam.family!r} in {path}")
        _validate_family(fam, units)
        families[fam.family] = fam

    return Dictionary(units=units, families=families)


def _validate_family(fam: Family, units: UnitRegistry) -> None:
    """Catch dictionary mistakes at load time rather than mid-demo."""
    keys = {a.key for a in fam.attributes}

    for attr in fam.attributes:
        if attr.unit and not units.try_resolve(attr.unit):
            raise ValueError(f"{fam.family}.{attr.key}: unknown unit {attr.unit!r}")

    missing_block = [k for k in fam.blocking.primary_key if k not in keys]
    if missing_block:
        raise ValueError(
            f"{fam.family}: blocking.primary_key references undefined attributes {missing_block}"
        )

    for gate in fam.gates:
        missing = [k for k in gate.attributes if k not in keys]
        if missing:
            raise ValueError(
                f"{fam.family}: gate {gate.id!r} references undefined attributes {missing}"
            )

    for group in fam.substitution_groups:
        if group.attribute not in keys:
            raise ValueError(
                f"{fam.family}: substitution group {group.id!r} references "
                f"undefined attribute {group.attribute!r}"
            )
        attr = fam.attribute(group.attribute)
        if attr and attr.values:
            unknown = [m for m in group.members if m not in attr.values]
            if unknown:
                raise ValueError(
                    f"{fam.family}: substitution group {group.id!r} lists values "
                    f"not in the {group.attribute!r} enum: {unknown}"
                )
