# Codification standards, and the precedent that reframes our pitch

## The single biggest reframing available to us

**India already operates a national item-codification authority.**

India has been a member of the NATO Codification System since 10 June 2008, with NATO
country code **72**, operated by the **Directorate of Standardisation, Ministry of Defence**
(branded NCB-India), which is also the sole issuer of NCAGE manufacturer codes to Indian
entities.

Sources: [ddpdos.gov.in/about-us](https://ddpdos.gov.in/about-us),
[NCAGE page](https://ddpdos.gov.in/ncb-india/nato-codification/ncage)

The NCS architecture is structurally the thing SIH26099 asks for:

- 13-digit NSN = Federal Supply Classification (4) + country code (2) + NIIN (7)
- The **NIIN is permanent** and never changes, even if the item is reclassified
- **One NSN is the canonical identity**, and many manufacturer part numbers (each tied to
  an NCAGE manufacturer code) and many national stock numbers map onto it
- **Item Name Code (INC)**, 5 digits, gives the standardised approved item name; items
  sharing an INC are functionally similar — this is exactly our "possible alternative"
  relation
- **MRC codes** carry the typed item characteristics

Reference: [ACodP-1 manual (PDF)](https://eportal.nspa.nato.int/ac135/data/pdf/ACodP1_E.pdf)

### What this means for our pitch

The Common National Material Code should **not** be an invented `SMP-000417` sequence.

> "We did not invent a national code. We took the structure India's own codification bureau
> has used since 2008 and extended it to civil public sector enterprises."

That sentence is dramatically stronger than anything a bare counter can support.

**Also confirmed, across two independent research passes: there is no existing "One Nation
One Material Code" initiative in India.** The gap is real, not already solved.

## Choosing the classification backbone (free vs paid matters)

| Standard | Structure | Typed attributes? | Cost |
|---|---|---|---|
| **UNSPSC** | 8-digit, 4 levels (Segment/Family/Class/Commodity) | **No attribute dictionary at all** | Codeset free to browse; official Excel is $275 |
| **eCl@ss ADVANCED** | 8-digit `XX-XX-XX-XX`, properties with stable IRDIs | Yes, rich | **Paid**, licensed per company by employee count |
| **ECCMA eOTD** (ISO 22745) | Open technical dictionary, language-independent concepts | **Yes** | **Free** |
| **ISO 8000-110 / -115** | Data quality requirements for master data exchange | n/a (rules) | Standard is paid; the rules are documented publicly |
| **IEC 61360 CDD / ISO 13584 PLIB** | Shares the IRDI mechanism with eCl@ss | Yes | Mixed |

**The correct architecture for a national system:** UNSPSC (or NCS FSC) for the
classification hierarchy, **plus** ISO 22745 / eOTD for the typed attribute dictionary,
**plus** ISO 8000-110 conformance for description quality rules. All free.

This turns "we made up a schema for bolts" into "we implemented an ISO standard's data
model" for the same amount of work.

> ⚠️ **Licence trap:** the free UNSPSC spreadsheet at
> [ungm.org/Public/UNSPSC/Excel](https://www.ungm.org/Public/UNSPSC/Excel) (13,336 rows,
> no login, verified working) is licensed **personal use only** and forbids commercial or
> public use and redistribution. Fine for prototyping. Not for anything we ship.

## Other standards worth knowing

- **Shell MESC** — 10-digit hierarchical code, developed 1932, industry-wide in oil and gas.
  Directly relevant to CPCL. Example code formats found only in secondary vendor sources,
  so treat specific examples as unverified.
- **HSN codes** — a standard SAP field (Control Code, Foreign Trade tab) used purely to
  determine GST rate. Tax classification riding alongside the material master, **not** a
  substitute for material identity.
- **GS1 / GTIN / GPC** — retail and consumer goods. Thin direct MRO relevance.
- **GeM** — roughly 11,220 product categories (2026). A taxonomy, not a cross-referenced
  item-identity system. Effectively superseded DGS&D, which closed 31 October 2017.
- **Indian Railways** — iMMS and the newer UDM manage stores ledgers. No public
  material-code scheme we could verify.
- **BIS** — national standards body. No evidence it operates a material-master
  classification system.
- **NIC codes** — classify economic activity, not materials. Not applicable.

## How real material master records are structured

**Noun-modifier convention** (NATO Item Name Directory, H6 manual): a general noun plus
extended modifiers, roughly 40,000 approved item names.

Pattern: **noun → design/type modifier → dimensional and material modifiers → applicable
standard → manufacturer series.**

Illustrative, built to the documented convention:
- `SCREW,CAP HEX HD M12X50 SS316 ISO4014`
- `BEARING,BALL DGBB 25X52X15 6205-2RS`

**SAP fields that matter to us:**

| Field | Meaning |
|---|---|
| `MATNR` | Material number (18 char) |
| `MAKTX` | Short description (40 char, table `MAKT`) |
| `MTART` | Material type (`ERSA` spares, `HERS` manufacturer-part records) |
| `MATKL` | Material group |
| `MEINS` | Base unit of measure |
| `MARM` | Alternative UoM per material: `MEINH`, `UMREZ` numerator, `UMREN` denominator |
| `MFRPN` | Manufacturer part number, in `MARA`, client-level |
| `CL02` / `CT04` | Classification: classes and characteristics, class type `001` for materials |

**Documented real-world UoM failure modes:** missing or wrong conversion factors entered by
users; wrongly assigned ISO UoM codes breaking IDoc interfaces; and the **same item
carrying different base units across plants** (EA vs SET), which blocks cross-plant demand
aggregation. That last one is a named SAP MDG-M validation target and makes a perfect demo
case.

## The money number for our opening slide

**CAG Report No. 10 of 2025 (Commercial), on SAIL**, tabled in Parliament 30 July 2025:

- **₹12,743 crore** in revenue and operational losses, FY2016-17 to FY2022-23, from
  ineffective procurement and inventory management
- Non-moving inventory ran **6.10%–8.38%** of total inventory against SAIL's own 3% norm
- Average inventory held: ₹21,698 crore

[Press release (PDF)](https://cag.gov.in/uploads/PressRelease/PR-Press-Release-on-inventory-management-in-SAIL-english-29-july-2025-06888b2af3f93c1-33115052.pdf)

Primary, audited, Government of India, named CPSE. **Present it honestly** — CAG frames it
as inventory mismanagement broadly, not specifically as duplicate material codes.

## Duplicate-rate figures: what is safe to cite

| Figure | Source | Safe to use? |
|---|---|---|
| ~7% duplicates at ElringKlinger | Sparetech, named company | Yes, with attribution |
| ~9% average across client base | Sparetech | Yes, vendor-published |
| 10–25% of active SKUs | Verusen | Yes, vendor-published |
| 5–7% of spend lost to duplicate purchases | Verdantis | Yes, methodology undisclosed |
| **"20–30% duplicate rate"** | **No traceable primary source** | **Do not use** |

If a judge has read the real literature, citing folklore is a credibility hit.
