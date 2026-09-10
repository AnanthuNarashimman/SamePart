"""Synthetic multi-organisation material master.

Seed identities use real published fastener values: ISO metric coarse thread diameters and
pitches, standard lengths, real property classes from ISO 3506 and ISO 898-1, and real
governing specifications. Generation only ever invents the *wording*, never a technical
value, so a domain reviewer looking at any single record sees a plausible real part.

Ground truth is written to a separate labels file. The catalogues the pipeline ingests
carry no identity column, so nothing downstream can accidentally read the answer.
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, asdict
from pathlib import Path

# ISO 261 / ISO 724 metric coarse series: diameter -> coarse pitch
COARSE = {6: 1.0, 8: 1.25, 10: 1.5, 12: 1.75, 16: 2.0, 20: 2.5, 24: 3.0}
LENGTHS = [16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120]
GRADES = ["A2-70", "A4-70", "8.8", "10.9", "12.9"]
STANDARDS = ["ISO4014", "ISO4017", "DIN931", "DIN933", "IS1364"]
FINISHES = ["PLAIN", "ZINCPLATED", "HOTDIPGALVANISED", "PASSIVATED"]

# Coined manufacturers, each marked (sim). Real supplier names were used here originally,
# which meant a screenshot could be mistaken for actual procurement data and implied that a
# real company had charged an invented price. Neither is acceptable in a demonstration.
MANUFACTURERS = [
    ("ANV", "Anvil Fastener Works (sim)"),
    ("TRD", "Trident Bolt & Nut Co (sim)"),
    ("KSL", "Kestrel Industrial Supply (sim)"),
    ("MRD", "Meridian Precision Fixings (sim)"),
    ("QRY", "Quarry Head Fasteners (sim)"),
]

ORGS = [
    ("CPCL", "Chennai Petroleum Corporation Limited (simulated)"),
    ("IOCL", "Indian Oil Corporation Limited (simulated)"),
    ("BPCL", "Bharat Petroleum Corporation Limited (simulated)"),
    ("NTPC", "NTPC Limited (simulated)"),
]

GRADE_WORDS = {
    "A2-70": ["A2-70", "A2 70", "SS304 A2-70", "AISI 304 A2-70", "STAINLESS A2-70"],
    "A4-70": ["A4-70", "A4 70", "SS316 A4-70", "AISI 316 A4-70"],
    "8.8":   ["8.8", "GR 8.8", "GRADE 8.8", "CLASS 8.8"],
    "10.9":  ["10.9", "GR 10.9", "GRADE 10.9", "CLASS 10.9"],
    "12.9":  ["12.9", "GR 12.9", "GRADE 12.9"],
}
STD_WORDS = {
    "ISO4014": ["ISO 4014", "ISO4014", "AS PER ISO 4014"],
    "ISO4017": ["ISO 4017", "ISO4017"],
    "DIN931":  ["DIN 931", "DIN931"],
    "DIN933":  ["DIN 933", "DIN933"],
    "IS1364":  ["IS 1364", "IS1364", "IS:1364"],
}
FINISH_WORDS = {
    "PLAIN": ["PLAIN", "SELF COLOUR", "BLACK"],
    "ZINCPLATED": ["ZINC PLATED", "ZP", "ELECTRO GALVANISED"],
    "HOTDIPGALVANISED": ["HOT DIP GALVANISED", "HDG", "GALVANISED"],
    "PASSIVATED": ["PASSIVATED", "PICKLED AND PASSIVATED"],
}

# Each simulated organisation writes descriptions in its own house style, which is exactly
# what makes the same physical bolt unrecognisable across two material masters.
STYLES = {
    "CPCL": "terse_caps",
    "IOCL": "verbose_titlecase",
    "BPCL": "abbreviated",
    "NTPC": "attribute_list",
}

UOM_CHOICES = ["EA", "EA", "EA", "BOX-100", "BOX-50", "C", "DOZ"]


@dataclass
class Identity:
    identity_id: str
    diameter: int
    pitch: float
    length: int
    grade: str
    standard: str
    finish: str
    head_type: str
    manufacturer: str | None
    mpn: str | None


@dataclass
class Row:
    source_code: str
    description: str
    uom: str
    quantity: float
    unit_price: float
    manufacturer: str
    mfr_part_no: str


def _mpn(ident: Identity) -> str:
    g = ident.grade.replace(".", "").replace("-", "")
    return f"HB{ident.diameter:02d}{ident.length:03d}{g}"


def _describe(ident: Identity, style: str, rng: random.Random, drop: set[str]) -> str:
    dia, ln = ident.diameter, ident.length
    grade = rng.choice(GRADE_WORDS[ident.grade]) if "grade" not in drop else ""
    std = rng.choice(STD_WORDS[ident.standard]) if "standard" not in drop else ""
    fin = rng.choice(FINISH_WORDS[ident.finish]) if "finish" not in drop else ""

    if style == "terse_caps":
        parts = [f"HEX BOLT M{dia}X{ln}", grade, std, fin]
    elif style == "verbose_titlecase":
        parts = [f"Bolt, Hexagon Head, M{dia} x {ln}mm",
                 f"Property Class {grade}" if grade else "",
                 f"Conforming to {std}" if std else "",
                 fin.title() if fin else ""]
    elif style == "abbreviated":
        parts = [f"BLT HEX HD M{dia}X{ln}MM", grade, std, fin]
    else:  # attribute_list
        parts = [f"BOLT HEX HEAD; DIA {dia}MM; LG {ln}MM",
                 f"GRADE {grade}" if grade else "",
                 std, fin]

    return "  ".join(p for p in parts if p).strip()


def build_identities(n: int, rng: random.Random) -> list[Identity]:
    seen: set[tuple] = set()
    out: list[Identity] = []
    while len(out) < n:
        dia = rng.choice(list(COARSE))
        ln = rng.choice([l for l in LENGTHS if l >= dia * 2])
        grade = rng.choice(GRADES)
        std = rng.choice(STANDARDS)
        fin = rng.choice(FINISHES)
        key = (dia, ln, grade, std, fin)
        if key in seen:
            continue
        seen.add(key)
        code, _ = rng.choice(MANUFACTURERS)
        ident = Identity(f"ID{len(out):05d}", dia, COARSE[dia], ln, grade, std, fin,
                         "HEX", code, None)
        ident.mpn = _mpn(ident)
        out.append(ident)
    return out


def generate(out_dir: Path, identities: int = 260, seed: int = 20260909) -> dict:
    """Write one CSV catalogue per simulated organisation, plus a labels file."""
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idents = build_identities(identities, rng)
    catalogues: dict[str, list[Row]] = {o: [] for o, _ in ORGS}
    labels: list[tuple[str, str, str]] = []
    counters = {o: 1 for o, _ in ORGS}

    for ident in idents:
        # Real masters do not hold every item in every organisation.
        holders = rng.sample([o for o, _ in ORGS], k=rng.choice([1, 2, 2, 3, 3, 4]))
        # A true market price per identity; each organisation deviates from it, which is
        # what the price-variance and aggregation views later expose.
        true_price = round(2.0 + ident.diameter * 0.55 + ident.length * 0.045
                           + (6.0 if ident.grade.startswith("A") else 0.0), 2)

        for org in holders:
            drop: set[str] = set()
            r = rng.random()
            if r < 0.10:
                drop.add("grade")        # a missing critical attribute
            elif r < 0.22:
                drop.add("standard")
            if rng.random() < 0.25:
                drop.add("finish")

            desc = _describe(ident, STYLES[org], rng, drop)
            uom = rng.choice(UOM_CHOICES)
            pack = {"EA": 1, "DOZ": 12, "BOX-50": 50, "BOX-100": 100, "C": 100}[uom]
            price = round(true_price * pack * rng.uniform(0.78, 1.46), 2)

            code = f"{org}-{counters[org]:06d}"
            counters[org] += 1
            has_mpn = rng.random() < 0.55
            catalogues[org].append(Row(
                source_code=code,
                description=desc,
                uom=uom,
                quantity=float(rng.choice([1, 1, 1, 5, 10, 25])),
                unit_price=price,
                manufacturer=ident.manufacturer if has_mpn else "",
                mfr_part_no=ident.mpn if has_mpn else "",
            ))
            labels.append((org, code, ident.identity_id))

    _seed_demo_cases(catalogues, labels, counters, rng)

    for org, rows in catalogues.items():
        path = out_dir / f"{org}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(asdict(rows[0])))
            w.writeheader()
            for row in rows:
                w.writerow(asdict(row))

    with (out_dir / "labels.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["org", "source_code", "truth_identity"])
        w.writerows(labels)

    return {
        "identities": len(idents),
        "records": sum(len(v) for v in catalogues.values()),
        "per_org": {k: len(v) for k, v in catalogues.items()},
        "out_dir": str(out_dir),
    }


def _seed_demo_cases(catalogues, labels, counters, rng) -> None:
    """The demo cases are placed deliberately, not left to chance in random generation."""
    def add(org: str, desc: str, identity: str, uom="EA", qty=1.0, price=41.0,
            mfr="", mpn="") -> None:
        code = f"{org}-{counters[org]:06d}"
        counters[org] += 1
        catalogues[org].append(Row(code, desc, uom, qty, price, mfr, mpn))
        labels.append((org, code, identity))

    # 1. Clean merge across three organisations, wildly different wording.
    add("CPCL", "HEX BOLT M16X80  A2-70  ISO 4014  PLAIN", "DEMO-CLEAN", "EA", 1, 41.00)
    add("IOCL", "Bolt, Hexagon Head, M16 x 80mm, Property Class A2-70, Conforming to ISO 4014",
        "DEMO-CLEAN", "BOX-100", 1, 4180.00)
    add("BPCL", "BLT HEX HD M16X80MM  SS304 A2-70  ISO4014", "DEMO-CLEAN", "C", 1, 4390.00)

    # 2. Grade conflict. Identical but for one critical attribute; must never merge.
    add("CPCL", "HEX BOLT M20X100  8.8  DIN 931  HDG", "DEMO-CONFLICT-A")
    add("NTPC", "BOLT HEX HEAD; DIA 20MM; LG 100MM; GRADE 10.9  DIN 931  HOT DIP GALVANISED",
        "DEMO-CONFLICT-B")

    # 3. Missing critical attribute. The system must ask rather than guess.
    add("CPCL", "HEX BOLT M12X60  ISO 4017  ZINC PLATED", "DEMO-INCOMPLETE")
    add("IOCL", "Bolt, Hexagon Head, M12 x 60mm, Property Class 8.8, Conforming to ISO 4017, Zinc Plated",
        "DEMO-INCOMPLETE")

    # 4. Contextual substitution. Same geometry, A2 against A4: alternative, not identical.
    add("BPCL", "BLT HEX HD M10X40MM  SS304 A2-70  ISO4014", "DEMO-ALT-A")
    add("NTPC", "BOLT HEX HEAD; DIA 10MM; LG 40MM; GRADE A4-70  ISO 4014", "DEMO-ALT-B")

    # 5. Identity evidence contradicting a critical conflict. Must refuse both ways.
    add("CPCL", "HEX BOLT M12X50  A2-70  ISO 4014", "DEMO-CONTRADICT",
        mfr="ANV", mpn="HB12050A270")
    add("IOCL", "Bolt, Hexagon Head, M12 x 90mm, Property Class A2-70, Conforming to ISO 4014",
        "DEMO-CONTRADICT-B", mfr="ANV", mpn="HB12050A270")
