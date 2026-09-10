"""The national code, where the right answer is exact and nothing else checks it.

The evaluation harness scores identity decisions. It never looks at the code minted for an
identity, so a broken check digit or a reclassification that silently renumbers a material
would pass every metric we publish. These are the properties the NATO Codification System
gets right and that a national scheme has to get right too: the identity is permanent, and
reclassification is a metadata change rather than a migration.
"""
from pathlib import Path

from samepart.pipeline.national_code import (
    CodeFormat, compose_full, compose_identity, luhn, parse, reclassify,
)

FMT = CodeFormat.from_file(Path("dictionaries/national_code.yaml"))


def test_luhn_matches_the_published_algorithm():
    """A fixed vector, so a rewrite of the loop cannot quietly change the answer."""
    assert luhn("7992739871") == 3


def test_luhn_catches_every_single_digit_slip():
    """The property the check digit exists for. Anything less and it is decoration.

    Note it catches every SINGLE-digit error, not every error: two changes can cancel, which
    is why `31161600` and `31171500` share a check digit on the same serial. That is expected
    Luhn behaviour, not a defect, and the exhaustive sweep below is over single changes only.
    """
    base = "311616000000417"
    correct = luhn(base)
    for position in range(len(base)):
        for replacement in "0123456789":
            if replacement == base[position]:
                continue
            typo = base[:position] + replacement + base[position + 1:]
            assert luhn(typo) != correct, f"a slip at position {position} went undetected"


def test_identity_carries_no_classification():
    """The permanent part must not encode anything that can later be revised, which is the
    whole reason a NIIN survives reclassification and a full NSN does not."""
    identity = compose_identity(FMT, 417)
    assert "0000417" in identity
    parsed = parse(FMT, identity)
    assert parsed.serial == 417
    assert parsed.classification in (None, "")


def test_full_code_carries_the_classification():
    full = compose_full(FMT, 417, "31161600")
    assert "31161600" in full
    assert parse(FMT, full).serial == 417


def test_reclassification_keeps_the_serial():
    """The one property that makes reclassification safe. If this fails, every cross-reference
    a CPSE holds against the old code is silently wrong."""
    before = compose_full(FMT, 417, "31161600")
    after = reclassify(FMT, before, "31171500")

    assert parse(FMT, after).serial == parse(FMT, before).serial == 417
    assert "31171500" in after
    assert before != after


def test_reclassified_code_still_validates():
    """A recomputed check digit, not the old one carried across."""
    after = reclassify(FMT, compose_full(FMT, 417, "31161600"), "40141600")
    parsed = parse(FMT, after)
    assert parsed.valid, f"{after} failed its own check digit after reclassification"


def test_parse_reports_a_corrupted_code_rather_than_raising():
    """Parsing returns a verdict with a reason instead of throwing, because the caller is a
    person who mistyped a code and needs to be told which digit is wrong."""
    good = compose_full(FMT, 417, "31161600")
    digit = "8" if good[-1] != "8" else "7"

    result = parse(FMT, good[:-1] + digit)
    assert not result.valid
    assert "check digit" in result.reason

    assert not parse(FMT, "NOT-A-CODE").valid
