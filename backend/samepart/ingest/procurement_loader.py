"""Reading a CPSE purchase order extract."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from samepart.units import UnitRegistry, UnknownUnitError

DEFAULT_COLUMN_MAP = {
    "source_code": "source_code",
    "po_number": "po_number",
    "line_no": "line_no",
    "po_date": "po_date",
    "vendor": "vendor",
    "vendor_part_number": "vendor_part_number",
    "plant": "plant",
    "quantity": "quantity",
    "uom": "uom",
    "unit_price": "unit_price",
    "currency": "currency",
}
REQUIRED = ("source_code", "po_number", "po_date")


@dataclass
class PORow:
    source_code: str
    po_number: str
    line_no: int
    po_date: date
    vendor: str | None = None
    vendor_part_number: str | None = None
    plant: str | None = None
    quantity: float | None = None
    uom: str | None = None
    base_quantity: float | None = None
    base_uom: str | None = None
    unit_price: float | None = None
    unit_price_base: float | None = None
    line_value: float | None = None
    currency: str = "INR"


@dataclass
class POLoadResult:
    rows: list[PORow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rows_read: int = 0


def _num(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def load_procurement_csv(content: bytes, units: UnitRegistry,
                         column_map: dict[str, str] | None = None) -> POLoadResult:
    mapping = {**DEFAULT_COLUMN_MAP, **(column_map or {})}
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig", errors="replace")))
    out = POLoadResult()

    headers = set(reader.fieldnames or [])
    missing = [mapping[f] for f in REQUIRED if mapping[f] not in headers]
    if missing:
        out.errors.append(f"required columns {missing} not found; file has {sorted(headers)}")
        return out

    def get(raw, key):
        v = raw.get(mapping.get(key, ""), None)
        return v.strip() if isinstance(v, str) and v.strip() else None

    for n, raw in enumerate(reader, start=2):
        out.rows_read += 1
        code, po, when = get(raw, "source_code"), get(raw, "po_number"), get(raw, "po_date")
        if not (code and po and when):
            out.errors.append(f"row {n}: missing source code, PO number or date, skipped")
            continue
        try:
            po_date = datetime.fromisoformat(when).date()
        except ValueError:
            out.errors.append(f"row {n}: unreadable date {when!r}, skipped")
            continue

        row = PORow(
            source_code=code, po_number=po,
            line_no=int(_num(get(raw, "line_no")) or 1), po_date=po_date,
            vendor=get(raw, "vendor"), vendor_part_number=get(raw, "vendor_part_number"),
            plant=get(raw, "plant"), quantity=_num(get(raw, "quantity")),
            uom=get(raw, "uom"), unit_price=_num(get(raw, "unit_price")),
            currency=get(raw, "currency") or "INR",
        )

        # Normalise here, at the boundary. A purchase of one box of a hundred and a purchase
        # of a hundred each must be comparable before any aggregation is valid.
        if row.uom:
            try:
                spec = units.resolve(row.uom)
                row.base_uom = spec.base
                if row.quantity is not None:
                    row.base_quantity = row.quantity * spec.factor
                if row.unit_price is not None:
                    row.unit_price_base = round(row.unit_price / spec.factor, 4)
            except UnknownUnitError:
                out.errors.append(f"row {n}: unrecognised unit {row.uom!r}, left unconverted")
        if row.quantity is not None and row.unit_price is not None:
            row.line_value = round(row.quantity * row.unit_price, 2)

        out.rows.append(row)
    return out
