"""Extraction on the lines that fooled it.

Each case here is a real generated description that was read wrongly, with the value it was
read as and the value it should have been. They are regression tests in the plain sense: the
gasket ones merged eighteen pairs of different gaskets as identical before the extractor
learned that a value next to "RING" belongs to the ring.
"""
import pytest

from samepart.api.deps import dictionary
from samepart.pipeline.extract import extract

GASKET = dictionary().family("gasket_spiral_wound")
BOLT = dictionary().family("hex_bolt")


def read(family, text: str) -> dict[str, object]:
    return {k: v.value for k, v in extract(family, text).items()}


@pytest.mark.parametrize("text, winding, ring", [
    # The defect: SS304 is first in the winding vocabulary and appears in the ring segment,
    # so every gasket with an SS304 ring extracted as an SS304 winding.
    ("GSKT SW 200NB CL300  MONEL  MICA  SS304 RING  ASME B16.20", "MONEL", "SS304"),
    ("GASKET SW 50NB 300#  MONEL  MICA GRAPHITE  SS304 RING  API601", "MONEL", "SS304"),
    # Both values are stainless, so only the anchor can tell them apart.
    ("GSKT SW 200NB CL300  SS 316  MICA GRAPHITE  SS 304 CENTRING RING  API 601", "SS316", "SS304"),
    ("GASKET SPIRAL WOUND; NB 50MM; CLASS 300  SS304  PTFE  CS RING  ASME B16.20", "SS304", "CS"),
    ("Gasket, Spiral Wound, 80mm NB, Class 150  Monel Winding  Graphite Filler  "
     "Carbon Steel Ring  To API 601", "MONEL", "CS"),
])
def test_ring_material_is_not_read_as_winding(text, winding, ring):
    got = read(GASKET, text)
    assert got["winding_material"] == winding
    assert got["outer_ring"] == ring


def test_longest_surface_form_wins_for_the_filler():
    """"MICA GRAPHITE" is a declared alias for MICA; a bare "GRAPHITE" inside it must not win."""
    assert read(GASKET, "GSKT SW 25NB CL150  SS316  MICA GRAPHITE  CS RING")["filler"] == "MICA"


def test_a_value_is_never_read_twice():
    """One SS304 in the line, next to RING: the ring gets it and the winding stays unknown
    rather than helping itself to the same word."""
    got = read(GASKET, "GSKT SW 100NB CL300  PTFE  SS304 RING  ASME B16.20")
    assert got["outer_ring"] == "SS304"
    assert got["winding_material"] is None


def test_longest_finish_still_wins_for_bolts():
    got = read(BOLT, "HEX BOLT M12X50  8.8  ISO4014  HOT DIP GALVANISED")
    assert got["finish"] == "HOTDIPGALVANISED"


def test_a_value_touching_other_characters_is_not_a_match():
    """"CS" must not be found inside "CLASS" or "ASME"."""
    got = read(GASKET, "GASKET SW 50NB CLASS 300  SS316  PTFE  ASME B16.20")
    assert got["outer_ring"] is None
