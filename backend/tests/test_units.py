"""Unit conversion, where a wrong answer is silently plausible.

Every other part of the pipeline announces its failures: a gate fires, a value comes back
`unknown`, a pair abstains. A unit conversion that is wrong by a factor produces a number that
looks entirely reasonable and quietly poisons every price comparison downstream. The
evaluation harness cannot see it — it scores identity decisions, not arithmetic — which is
exactly why these are tests and not metrics.
"""
from pathlib import Path

import pytest

from samepart.units import IncompatibleUnitsError, UnitRegistry

REGISTRY = UnitRegistry.from_file(Path("dictionaries/units.yaml"))


def test_metre_and_per_thousand_are_not_the_same_unit():
    """`m` is a metre and `M` is per-thousand. This collision is real and it cost us once.

    Case-insensitive alias lookup resolved `m` to the packaging code, so a length in metres
    became a count in thousands. The registry now matches codes case-sensitively before it
    ever consults aliases; if that ordering is reversed this test fails and the price
    comparisons stay correct.
    """
    metre = REGISTRY.resolve("m")
    per_thousand = REGISTRY.resolve("M")
    assert metre.code != per_thousand.code
    assert metre.dimension != per_thousand.dimension


def test_case_insensitive_lookup_still_works_where_it_is_unambiguous():
    """Fixing the collision must not break `KG`, which no reasonable person writes as `kg`."""
    assert REGISTRY.resolve("KG").code == REGISTRY.resolve("kg").code


def test_to_base_scales_by_the_declared_factor():
    """Length is based in millimetres, so two metres is two thousand of them."""
    value, base = REGISTRY.to_base(2.0, "m")
    assert base == "mm"
    assert value == pytest.approx(2000.0)


def test_convert_round_trips():
    assert REGISTRY.convert(REGISTRY.convert(5.0, "kg", "g"), "g", "kg") == pytest.approx(5.0)
    assert REGISTRY.convert(1.0, "in", "mm") == pytest.approx(25.4)


def test_cross_dimension_conversion_is_refused_not_guessed():
    """Metres to kilograms needs a density. Guessing one would be the worst possible failure:
    a plausible number with no basis."""
    with pytest.raises(IncompatibleUnitsError):
        REGISTRY.convert(1.0, "mm", "kg")


def test_unit_price_in_base_divides_by_the_pack():
    """A box of 100 at 4180 is 41.80 each. Comparing a box price against an each price is the
    single most common way a cross-organisation price comparison goes wrong."""
    assert REGISTRY.unit_price_in_base(4180.0, 1.0, "BOX-100") == pytest.approx(41.80, abs=0.01)
