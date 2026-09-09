"""Synthetic purchase order history.

Generated on top of the material catalogues, so every line refers to a real source code.
Three properties are deliberate, because each one is what makes a downstream capability
demonstrable rather than decorative.

- **Price spread across CPSEs for the same true identity.** Each organisation negotiates
  around a market price, so demand aggregation has something real to find
- **Vendor overlap.** The same vendor and vendor part number sometimes appears in two CPSEs'
  history for the same identity, which is independent identity evidence the description
  cannot give
- **Dead codes.** A deliberate share of material codes have no purchase order at all in the
  window, which is exactly what legacy rationalisation is supposed to surface
"""
from __future__ import annotations

import csv
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

VENDORS = [
    ("Sundram Fasteners Ltd", "SUN"),
    ("TVS Srichakra Fasteners", "TVS"),
    ("Unbrako India Pvt Ltd", "UNB"),
    ("Precision Fasteners Ltd", "PFL"),
    ("Kalpataru Industrial Supply", "KIS"),
    ("Gujarat Bolt & Nut Co", "GBN"),
]
PLANTS = {
    "CPCL": ["Manali Refinery", "Cauvery Basin Refinery"],
    "IOCL": ["Panipat Refinery", "Paradip Refinery", "Mathura Refinery"],
    "BPCL": ["Kochi Refinery", "Mumbai Refinery"],
    "NTPC": ["Vindhyachal STPS", "Korba STPS", "Ramagundam STPS"],
}
UOMS = ["EA", "EA", "EA", "BOX-100", "C", "DOZ"]
PACK = {"EA": 1, "DOZ": 12, "BOX-50": 50, "BOX-100": 100, "C": 100}

WINDOW_START = date(2022, 4, 1)
WINDOW_END = date(2026, 3, 31)


@dataclass
class POLine:
    source_code: str
    po_number: str
    line_no: int
    po_date: str
    vendor: str
    vendor_part_number: str
    plant: str
    quantity: float
    uom: str
    unit_price: float
    currency: str = "INR"


def generate(out_dir: Path, catalogues: dict[str, list[dict]], truth: dict[str, str],
             seed: int = 4242) -> dict:
    """catalogues: org -> the rows written to that org's CSV. truth: source_code -> identity."""
    rng = random.Random(seed)
    out_dir = Path(out_dir)

    # One market price per true identity, so cross-CPSE variance is a real signal.
    market: dict[str, float] = {}
    # A preferred vendor per identity, shared across CPSEs often enough to be evidence.
    preferred: dict[str, tuple[str, str]] = {}

    summary = {}
    for org, rows in catalogues.items():
        lines: list[POLine] = []
        po_seq = 1
        for row in rows:
            code = row["source_code"]
            identity = truth.get(code, code)
            base = market.setdefault(identity, round(rng.uniform(6.0, 190.0), 2))
            vendor_name, vendor_prefix = preferred.setdefault(identity, rng.choice(VENDORS))

            # A deliberate share of codes were never ordered in the window. These are the
            # dead codes that legacy rationalisation exists to find.
            if rng.random() < 0.18:
                continue

            for _ in range(rng.choice([1, 1, 2, 2, 3, 4, 6])):
                # Each CPSE negotiates around the market price, and prices drift over time.
                offset = (WINDOW_END - WINDOW_START).days
                when = WINDOW_START + timedelta(days=rng.randint(0, offset))
                drift = 1.0 + 0.06 * ((when - WINDOW_START).days / max(offset, 1))
                org_factor = rng.uniform(0.82, 1.34)

                uom = rng.choice(UOMS)
                pack = PACK[uom]
                unit_price = round(base * org_factor * drift * pack, 2)

                # Usually the preferred vendor, sometimes a different one.
                if rng.random() < 0.75:
                    v_name, v_pre = vendor_name, vendor_prefix
                else:
                    v_name, v_pre = rng.choice(VENDORS)

                lines.append(POLine(
                    source_code=code,
                    po_number=f"{org}/PO/{when.year}/{po_seq:05d}",
                    line_no=rng.choice([1, 1, 1, 2, 3]),
                    po_date=when.isoformat(),
                    vendor=v_name,
                    vendor_part_number=f"{v_pre}-{identity[-5:]}",
                    plant=rng.choice(PLANTS.get(org, ["Central Stores"])),
                    quantity=float(rng.choice([1, 2, 5, 10, 20, 50, 100, 250])),
                    uom=uom,
                    unit_price=unit_price,
                ))
                po_seq += 1

        path = out_dir / f"{org}_procurement.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(asdict(lines[0])))
            w.writeheader()
            for line in lines:
                w.writerow(asdict(line))
        summary[org] = len(lines)

    return {"lines_per_org": summary, "total_lines": sum(summary.values())}
