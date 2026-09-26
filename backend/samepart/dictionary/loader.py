"""Loads the YAML dictionaries into typed objects at startup."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from samepart.dictionary.models import Family
from samepart.units import UnitRegistry


@dataclass
class Dictionary:
    units: UnitRegistry
    families: dict[str, Family]
    # Names of families that came from the runtime directory rather than the repository.
    added: set[str] = field(default_factory=set)

    def family(self, name: str) -> Family:
        try:
            return self.families[name]
        except KeyError:
            known = ", ".join(sorted(self.families)) or "none"
            raise KeyError(f"unknown family {name!r}; loaded families: {known}") from None

    @property
    def family_names(self) -> list[str]:
        return sorted(self.families)


def load_dictionary(root: Path, added_dir: Path | None = None) -> Dictionary:
    """Built-in families from the repository, then any added at runtime.

    A family added through the API is written to `added_dir` and read back here on the next
    boot, so it survives a restart. One with the same name as a built-in family replaces it:
    that is what "replace" on the endpoint means, and it is the only way a running deployment
    can correct a family without a code change.
    """
    root = Path(root)
    units = UnitRegistry.from_file(root / "units.yaml")

    families: dict[str, Family] = {}
    for path in sorted((root / "families").glob("*.yaml")):
        fam = parse_family(path.read_text(), units)
        if fam.family in families:
            raise ValueError(f"duplicate family {fam.family!r} in {path}")
        families[fam.family] = fam

    added: set[str] = set()
    if added_dir is not None and Path(added_dir).is_dir():
        for path in sorted(Path(added_dir).glob("*.yaml")):
            fam = parse_family(path.read_text(), units)
            families[fam.family] = fam
            added.add(fam.family)

    return Dictionary(units=units, families=families, added=added)


def parse_family(yaml_text: str, units: UnitRegistry) -> Family:
    """One family from its YAML, validated. Raises ValueError with a message a person can act
    on: the unit or attribute that is wrong, not a stack trace."""
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"not valid YAML: {exc}") from None
    if not isinstance(raw, dict):
        raise ValueError("expected a YAML mapping with at least `family`, `label`, `naming` "
                         "and `attributes`")
    try:
        fam = Family.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'document'}: {e['msg']}"
            for e in exc.errors()[:6])
        raise ValueError(problems) from None
    _validate_family(fam, units)
    return fam


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
