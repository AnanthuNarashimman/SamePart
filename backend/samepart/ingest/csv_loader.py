"""Reading a CPSE catalogue export.

Every organisation exports different column headings for the same facts, so the mapping is
configuration supplied per source, never a hardcoded parser. `DEFAULT_COLUMN_MAP` covers the
generated catalogues; a real CPSE export supplies its own.

Quantities are converted to base units here, at the boundary. Nothing downstream should ever
see a price of 4180 for a box of a hundred and try to compare it with 41.80 for one.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from samepart.units import UnitRegistry, UnknownUnitError

# canonical field -> the header it is likely to appear under
DEFAULT_COLUMN_MAP = {
    "source_code": "source_code",
    "description": "description",
    "uom": "uom",
    "quantity": "quantity",
    "unit_price": "unit_price",
    "manufacturer": "manufacturer",
    "manufacturer_part_number": "mfr_part_no",
    "stock_on_hand": "stock_on_hand",
    "last_issue_date": "last_issue_date",
}

REQUIRED = ("source_code", "description")


@dataclass
class Row:
    source_code: str
    description: str
    row_ref: str
    uom: str | None = None
    base_uom: str | None = None
    quantity: float | None = None
    base_quantity: float | None = None
    unit_price: float | None = None
    unit_price_base: float | None = None
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    stock_on_hand: float | None = None
    stock_base_qty: float | None = None
    last_issue_date: str | None = None


@dataclass
class LoadResult:
    rows: list[Row] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rows_read: int = 0


def _num(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def load_csv(content: bytes, units: UnitRegistry,
             column_map: dict[str, str] | None = None) -> LoadResult:
    mapping = {**DEFAULT_COLUMN_MAP, **(column_map or {})}
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out = LoadResult()

    headers = set(reader.fieldnames or [])
    for field_name in REQUIRED:
        if mapping[field_name] not in headers:
            out.errors.append(
                f"required column {mapping[field_name]!r} (for {field_name}) not found; "
                f"file has {sorted(headers)}"
            )
    if out.errors:
        return out

    def get(raw: dict, key: str) -> str | None:
        col = mapping.get(key)
        v = raw.get(col) if col else None
        return v.strip() if isinstance(v, str) and v.strip() else None

    for n, raw in enumerate(reader, start=2):   # row 1 is the header
        out.rows_read += 1
        code, desc = get(raw, "source_code"), get(raw, "description")
        if not code or not desc:
            out.errors.append(f"row {n}: missing source code or description, skipped")
            continue

        row = Row(source_code=code, description=desc, row_ref=f"row {n}",
                  uom=get(raw, "uom"),
                  quantity=_num(get(raw, "quantity")),
                  unit_price=_num(get(raw, "unit_price")),
                  manufacturer=get(raw, "manufacturer"),
                  manufacturer_part_number=get(raw, "manufacturer_part_number"),
                  stock_on_hand=_num(get(raw, "stock_on_hand")),
                  last_issue_date=get(raw, "last_issue_date"))

        if row.uom:
            try:
                spec = units.resolve(row.uom)
                row.base_uom = spec.base
                if row.quantity is not None:
                    row.base_quantity = row.quantity * spec.factor
                if row.unit_price is not None:
                    # unit_price is the price of ONE issue unit, so one box of a hundred
                    # costs unit_price and each costs unit_price / 100.
                    row.unit_price_base = round(row.unit_price / spec.factor, 4)
                if row.stock_on_hand is not None:
                    # Stock is held in the issue unit too. A hundred boxes is ten thousand
                    # each, and comparing that with someone else's "10,000" unnormalised is
                    # how a transfer recommendation becomes nonsense.
                    row.stock_base_qty = row.stock_on_hand * spec.factor
            except UnknownUnitError:
                out.errors.append(f"row {n}: unrecognised unit {row.uom!r}, left unconverted")

        out.rows.append(row)

    return out
