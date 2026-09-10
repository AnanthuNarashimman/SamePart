"""The dictionaries are data, which means a typo in them is a runtime failure, not a syntax
error.

Families are added by writing YAML, and the whole design argument depends on that being safe.
A gate naming an attribute that does not exist, a blocking key that was renamed, a synthesis
block whose identity keys are a subset of what actually distinguishes an identity — none of
those raise on load. They surface later as a family that quietly decides nothing, or as the
part-number collision that made our best tier our worst.

This walks every family, so a new one is checked the moment it is dropped in.
"""
import pytest

from samepart.api.deps import dictionary

DICT = dictionary()
FAMILIES = sorted(DICT.families)


def test_at_least_one_family_loads():
    assert FAMILIES, "no families loaded; the dictionary directory is empty or unreadable"


@pytest.mark.parametrize("name", FAMILIES)
def test_every_gate_names_attributes_that_exist(name):
    """A gate referencing a renamed attribute silently never fires."""
    family = DICT.family(name)
    keys = {a.key for a in family.attributes}
    for gate in family.gates:
        unknown = [k for k in gate.attributes if k not in keys]
        assert not unknown, f"{name}: gate {gate.id!r} names unknown attributes {unknown}"


@pytest.mark.parametrize("name", FAMILIES)
def test_blocking_keys_exist_and_are_not_derived(name):
    """Blocking on a derived attribute would key retrieval on something computed from the very
    values the pair is being compared on."""
    family = DICT.family(name)
    by_key = {a.key: a for a in family.attributes}
    for key in family.blocking.primary_key:
        assert key in by_key, f"{name}: blocking key {key!r} is not an attribute"
        assert not by_key[key].is_derived, f"{name}: blocking on derived attribute {key!r}"


@pytest.mark.parametrize("name", FAMILIES)
def test_substitution_groups_reference_real_attributes_and_values(name):
    family = DICT.family(name)
    by_key = {a.key: a for a in family.attributes}
    for group in family.substitution_groups:
        assert group.attribute in by_key, (
            f"{name}: substitution group {group.id!r} names unknown attribute "
            f"{group.attribute!r}")
        declared = by_key[group.attribute].values
        if declared:
            stray = [m for m in group.members if m not in declared]
            assert not stray, (
                f"{name}: substitution group {group.id!r} lists values {stray} that are not in "
                f"the attribute's declared value set")


@pytest.mark.parametrize("name", FAMILIES)
def test_synthesis_identity_keys_cover_everything_that_distinguishes_an_identity(name):
    """The defect that made our highest-precision tier our largest source of false merges.

    The generator builds a part number from `identity_keys`. If a pooled attribute that
    varies between identities is missing from that list, two different identities get the same
    part number and the identity tier merges them on fabricated evidence. It cost 15 false
    merges and was invisible until the evaluation harness existed.
    """
    family = DICT.family(name)
    if not family.synthesis:
        pytest.skip(f"{name} declares no synthesis block")

    synth = family.synthesis
    varying = {key for key, pool in synth.pools.items() if len(set(map(str, pool))) > 1}
    missing = varying - set(synth.identity_keys)

    # An attribute may be deliberately excluded when it is informational — it varies but does
    # not make the item a different item.
    excusable = {k for k in missing
                 if (a := family.attribute(k)) and a.criticality.value == "informational"}

    assert not (missing - excusable), (
        f"{name}: {sorted(missing - excusable)} vary between identities but are absent from "
        f"identity_keys, so two identities can share a part number")


@pytest.mark.parametrize("name", FAMILIES)
def test_unregistered_forms_are_genuinely_unregistered(name):
    """The honesty guard on the benchmark.

    `unregistered` exists so the generator emits wording the extractor has never been told
    about. If one of those forms is also in the attribute's `value_aliases`, extraction reads
    it perfectly and the noise measures nothing.
    """
    family = DICT.family(name)
    if not family.synthesis:
        pytest.skip(f"{name} declares no synthesis block")

    for key, by_value in family.synthesis.unregistered.items():
        attribute = family.attribute(key)
        assert attribute, f"{name}: unregistered forms for unknown attribute {key!r}"
        known = {alias.upper() for alias in attribute.value_aliases}
        known |= {str(v).upper() for v in attribute.values}
        for forms in by_value.values():
            leaked = [f for f in forms if f.upper() in known]
            assert not leaked, (
                f"{name}.{key}: {leaked} are listed as unregistered but the extractor already "
                f"knows them, so they add no difficulty")


@pytest.mark.parametrize("name", FAMILIES)
def test_every_synthesis_template_only_uses_real_attributes(name):
    """A placeholder for an attribute that does not exist renders as a literal brace in a
    description and poisons extraction for that whole house style."""
    import re

    family = DICT.family(name)
    if not family.synthesis:
        pytest.skip(f"{name} declares no synthesis block")

    synth = family.synthesis
    available = {a.key for a in family.attributes} | set(synth.pools) | set(synth.derived)
    for style, template in synth.templates.items():
        unknown = [k for k in re.findall(r"\{([a-z0-9_]+)\}", template) if k not in available]
        assert not unknown, f"{name}: template {style!r} uses unknown placeholders {unknown}"
