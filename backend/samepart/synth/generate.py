"""Synthetic multi-organisation material master, driven entirely by the dictionary.

The pipeline never hardcoded a material family. This file did — an `Identity` dataclass with
`diameter` and `length` fields, and four literal description templates full of `HEX BOLT` —
which left the project's central claim, that families are data, unprovable. Adding a family
meant editing Python.

Everything a family needs is now in its own YAML under `synthesis:`, so a new family really is
one file and can be added in front of an evaluator.

Every technical value comes from the family file and every value there is real: ISO 261 / ISO
724 metric coarse threads, ISO 3506 and ISO 898-1 property classes, ASME B16.5 flange classes.
Generation invents the *wording*, never a value, so a domain reviewer looking at any single
record sees a plausible real part.

Ground truth is written to a separate labels file. The catalogues the pipeline ingests carry no
identity column, so nothing downstream can accidentally read the answer.
"""
from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

WINDOW_END = date(2026, 3, 31)
DICTIONARY_ROOT = Path("dictionaries")

PACK_SIZE = {"EA": 1, "DOZ": 12, "BOX-50": 50, "BOX-100": 100, "C": 100}
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")


def _house_styles(root: Path = DICTIONARY_ROOT) -> tuple[list[tuple[str, str]], dict[str, str],
                                                          dict[str, dict]]:
    """Who writes in which style, and how that style joins its segments."""
    spec = yaml.safe_load((root / "house_styles.yaml").read_text())
    orgs = [(o["code"], o["name"]) for o in spec["organisations"]]
    style_of = {o["code"]: o["style"] for o in spec["organisations"]}
    return orgs, style_of, spec["styles"]


ORGS, STYLE_OF, STYLE_SPEC = _house_styles()


@dataclass
class Identity:
    """One real-world item. `values` holds whatever attributes its family defines."""
    identity_id: str
    family: str
    values: dict[str, Any]
    manufacturer: str
    mpn: str


@dataclass
class Row:
    source_code: str
    description: str
    uom: str
    quantity: float
    unit_price: float
    manufacturer: str
    mfr_part_no: str
    stock_on_hand: float = 0.0
    last_issue_date: str = ""


def _surface(synth, key: str, value: Any, rng: random.Random) -> str:
    """One way a person might have written this value.

    Draws from `unregistered` at `noise_rate`: forms deliberately absent from the attribute's
    value_aliases. Without them the generator would only ever produce wording the extractor
    already knows, extraction would score 100% by construction, and the benchmark could not
    fail. A real master is full of wording nobody anticipated.
    """
    text = str(value)
    unknown = (synth.unregistered.get(key) or {}).get(text)
    if unknown and rng.random() < synth.noise_rate:
        return rng.choice(unknown)
    known = (synth.words.get(key) or {}).get(text)
    return rng.choice(known) if known else text


def _describe(synth, ident: Identity, style: str, rng: random.Random, drop: set[str]) -> str:
    """Render one house style's line, dropping any segment whose value was not recorded.

    Segments are separated by `|` in the template. A segment is dropped when a placeholder it
    contains resolved to nothing, so "Property Class {grade}" disappears entirely rather than
    leaving a dangling label — which is what a real master looks like when a field is blank.
    """
    template = synth.templates.get(style) or next(iter(synth.templates.values()))
    spec = STYLE_SPEC.get(style, {})
    out: list[str] = []

    for segment in template.split("|"):
        keys = PLACEHOLDER.findall(segment)
        if any(k in drop or ident.values.get(k) is None for k in keys):
            continue
        rendered = segment
        for k in keys:
            word = _surface(synth, k, ident.values[k], rng)
            if spec.get("case") == "title_values" and word.isupper() and len(word) > 3:
                word = word.title()
            rendered = rendered.replace("{" + k + "}", word)
        rendered = rendered.strip()
        if rendered:
            out.append(rendered)

    return spec.get("separator", "  ").join(out).strip()


def _part_number(synth, values: dict[str, Any]) -> str:
    """A part number names the maker's item, so it is a function of exactly the attributes
    that make one item different from another — `identity_keys`, and nothing else.

    It once encoded a subset of them, so two identities differing only in standard shared a
    part number and the identity tier merged them on fabricated evidence. Deriving it from the
    declared identity keys makes that class of defect impossible to reintroduce.
    """
    parts = []
    for key in synth.identity_keys:
        token = re.sub(r"[^A-Z0-9]", "", str(values.get(key, "")).upper())
        parts.append(token[:6] or "X")
    return synth.part_number_prefix + "".join(parts)


def _equivalence_map(fam) -> dict[str, dict[str, str]]:
    """Values the family declares interchangeable, folded onto one representative.

    The dictionary says DIN 931 was superseded by ISO 4014 and the two are dimensionally
    interchangeable, so the gates treat a record citing either as citing the same
    specification. The generator did not, and minted a separate identity for each — which
    made every such pair look like a false merge when it was the labels disagreeing with the
    domain rules the same file declares. A generator driven by the dictionary has to honour
    all of it, not only the parts that are convenient.
    """
    out: dict[str, dict[str, str]] = {}
    for group in fam.substitution_groups:
        relation = getattr(group.relation, "value", group.relation)
        if relation != "equivalent" or len(group.members) < 2:
            continue
        canonical = group.members[0]
        out.setdefault(group.attribute, {}).update({m: canonical for m in group.members})
    return out


def build_identities(synth, family: str, rng: random.Random,
                     equivalent: dict[str, dict[str, str]] | None = None) -> list[Identity]:
    equivalent = equivalent or {}
    keys = [k for k in synth.pools]
    seen: set[tuple] = set()
    out: list[Identity] = []
    attempts = 0

    while len(out) < synth.identities and attempts < synth.identities * 200:
        attempts += 1
        values = {k: rng.choice(synth.pools[k]) for k in keys}

        if any(values[c.key] < values[c.at_least_times] * c.factor
               for c in synth.constraints
               if c.key in values and c.at_least_times in values):
            continue

        for key, rule in synth.derived.items():
            source = values.get(rule["from"])
            values[key] = (rule.get("map") or {}).get(source)

        # Two records differing only in values the family calls equivalent are one identity.
        signature = tuple(
            equivalent.get(k, {}).get(str(values[k]), values[k])
            for k in synth.identity_keys)
        if signature in seen:
            continue
        seen.add(signature)

        code, _ = rng.choice(synth.manufacturers)
        out.append(Identity(
            identity_id=f"{family[:2].upper()}{len(out):05d}",
            family=family,
            values=values,
            manufacturer=code,
            mpn=_part_number(synth, values),
        ))
    return out


def _price(synth, values: dict[str, Any]) -> float:
    total = synth.price.base
    for key, rate in synth.price.per.items():
        v = values.get(key)
        if isinstance(v, (int, float)):
            total += v * rate
    for key, rules in synth.price.add_when.items():
        text = str(values.get(key, ""))
        for prefix, amount in rules.items():
            if text.startswith(prefix):
                total += amount
    return round(total, 2)


def generate(out_dir: Path, seed: int = 20260909, dictionary=None) -> dict:
    """Write one CSV per organisation per family, plus one labels file for all of them."""
    from samepart.api.deps import dictionary as load_dictionary

    d = dictionary or load_dictionary()
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    families = [f for f in d.families.values() if f.synthesis]
    if not families:
        raise RuntimeError("No family declares a `synthesis:` block; nothing to generate.")

    catalogues: dict[tuple[str, str], list[Row]] = {}
    labels: list[tuple[str, str, str]] = []
    counters = {code: 1 for code, _ in ORGS}
    per_family: dict[str, int] = {}

    for fam in families:
        synth = fam.synthesis
        idents = build_identities(synth, fam.family, rng, _equivalence_map(fam))
        per_family[fam.family] = len(idents)

        for org, _ in ORGS:
            catalogues.setdefault((org, fam.family), [])

        for ident in idents:
            # Real masters do not hold every item in every organisation.
            holders = rng.sample([o for o, _ in ORGS], k=rng.choice([1, 2, 2, 3, 3, 4]))
            true_price = _price(synth, ident.values)

            # Bound as defaults, not closed over: the helper is called inside this iteration
            # only, but binding makes that a property of the code rather than of the caller.
            def emit(org: str, *, synth=synth, ident=ident, true_price=true_price,
                     fam=fam) -> None:
                drop = {k for k, p in synth.drop.items() if rng.random() < p}
                desc = _describe(synth, ident, STYLE_OF[org], rng, drop)
                uom = rng.choice(synth.uom_choices)
                pack = PACK_SIZE.get(uom, 1)
                price = round(true_price * pack * rng.uniform(0.78, 1.46), 2)

                code = f"{org}-{counters[org]:06d}"
                counters[org] += 1
                has_mpn = rng.random() < 0.55

                # Stock on hand, in the issue unit. Three populations, because a real stores
                # ledger has all three and redistribution only exists because of the third:
                # actively consumed, empty, and a pile nobody has touched in years. Drawn in
                # BASE units then expressed in the issue unit — drawing in issue units and
                # multiplying up once produced 150,000 bolts in a single depot.
                roll = rng.random()
                if roll < 0.34:
                    base_stock, last_issue = 0.0, ""
                elif roll < 0.80:
                    base_stock = float(rng.choice([40, 80, 150, 300, 600]))
                    last_issue = (WINDOW_END - timedelta(days=rng.randint(5, 240))).isoformat()
                else:
                    base_stock = float(rng.choice([400, 800, 1200, 2000, 3500]))
                    last_issue = (WINDOW_END - timedelta(days=rng.randint(900, 1800))).isoformat()

                catalogues[(org, fam.family)].append(Row(
                    source_code=code,
                    description=desc,
                    uom=uom,
                    quantity=float(rng.choice([1, 1, 1, 5, 10, 25])),
                    unit_price=price,
                    manufacturer=ident.manufacturer if has_mpn else "",
                    mfr_part_no=ident.mpn if has_mpn else "",
                    stock_on_hand=round(base_stock / pack, 2) if base_stock else 0.0,
                    last_issue_date=last_issue,
                ))
                labels.append((org, code, ident.identity_id))

            for org in holders:
                emit(org)
                # A second plant, a later era, a re-keyed spares list: the same organisation
                # entering the same item again under a new code. Same house style, because it
                # is the same organisation, but its own draw of wording, blanks, unit and
                # price — which is what makes these hard rather than exact-text duplicates.
                extras = 0
                while (extras < synth.duplicate_within_org_max
                       and rng.random() < synth.duplicate_within_org):
                    emit(org)
                    extras += 1

    if "hex_bolt" in {f.family for f in families}:
        _seed_demo_cases(catalogues, labels, counters, rng)

    written: list[str] = []
    for (org, fam_name), rows in catalogues.items():
        if not rows:
            continue
        path = out_dir / f"{org}__{fam_name}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(asdict(rows[0])))
            w.writeheader()
            for row in rows:
                w.writerow(asdict(row))
        written.append(path.name)

    with (out_dir / "labels.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["org", "source_code", "truth_identity"])
        w.writerows(labels)

    per_org: dict[str, int] = {}
    for (org, _), rows in catalogues.items():
        per_org[org] = per_org.get(org, 0) + len(rows)

    return {
        "families": per_family,
        "identities": sum(per_family.values()),
        "records": sum(len(v) for v in catalogues.values()),
        "per_org": per_org,
        "files": written,
        "out_dir": str(out_dir),
    }


def _seed_demo_cases(catalogues, labels, counters, rng) -> None:
    """The demo cases are placed deliberately, not left to chance in random generation."""
    def add(org: str, desc: str, identity: str, uom="EA", qty=1.0, price=41.0,
            mfr="", mpn="", stock=0.0, last_issue="") -> None:
        code = f"{org}-{counters[org]:06d}"
        counters[org] += 1
        catalogues[(org, "hex_bolt")].append(
            Row(code, desc, uom, qty, price, mfr, mpn, stock, last_issue))
        labels.append((org, code, identity))

    # 1. Clean merge across three organisations, wildly different wording.
    add("CPCL", "HEX BOLT M16X80  A2-70  ISO 4014  PLAIN", "DEMO-CLEAN", "EA", 1, 41.00)
    add("IOCL", "Bolt, Hexagon Head, M16 x 80mm, Property Class A2-70, Conforming to ISO 4014",
        "DEMO-CLEAN", "BOX-100", 1, 4180.00)
    add("BPCL", "BLT HEX HD M16X80MM  SS304 A2-70  ISO4014", "DEMO-CLEAN", "C", 1, 4390.00,
        stock=6.0, last_issue="2022-11-04")   # 600 each, untouched for over three years

    # 2. Grade conflict. Identical but for one critical attribute; must never merge.
    add("CPCL", "HEX BOLT M20X100  8.8  DIN 931  HDG", "DEMO-CONFLICT-A")
    add("NTPC", "BOLT HEX HEAD; DIA 20MM; LG 100MM; GRADE 10.9  DIN 931  HOT DIP GALVANISED",
        "DEMO-CONFLICT-B")

    # 3. Missing critical attribute. The system must ask rather than guess.
    add("CPCL", "HEX BOLT M12X60  ISO 4017  ZINC PLATED", "DEMO-INCOMPLETE")
