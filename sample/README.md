# Demo upload files

Two material-master exports to upload live on the Import page. Each is a real CPSE-shaped
file — one family per file, because an import is run against one family — and every value in
them comes from the dictionaries, not from imagination:
`dictionaries/families/hex_bolt.yaml`, `dictionaries/families/bearing_ball.yaml`,
`dictionaries/units.yaml`, `dictionaries/column_aliases.yaml` and
`dictionaries/house_styles.yaml`.

Source codes are in a 9000xx range so they cannot collide with seeded records; an import
skips a code the organisation already holds.

| File | Import as | Family | Rows |
|---|---|---|---|
| `BPCL_hex_bolts_sample.csv` | BPCL steward (or the national approver) | Bolt, hex head | 14 |
| `IOCL_ball_bearings_sample.csv` | IOCL steward (or the national approver) | Bearing, deep groove ball | 12 |

A steward may import only for their own organisation, so sign in as `bpcl` for the first and
`iocl` for the second — or as `national`, which may import for either.

**Pick the family in the form.** The page defaults to whatever the dictionary loaded first;
a bearing file imported as bolts reads no attributes and reports success.

## What each file is built to show

### `BPCL_hex_bolts_sample.csv` — plain headers, BPCL's house style
Written in BPCL's declared style ("Heavily abbreviated": `BLT HEX HD M10X40MM  …`), with the
column names the loader expects, so it maps itself with nothing to correct.

Every verdict below was run through the real cascade, not predicted:

| Rows | What happens | Why |
|---|---|---|
| `900101` + `900102` | **Same material**, attribute tier | One writes `GRADE 8.8 / DIN 933 / ZINC PLATED`, the other `8.8 / DIN933 / ZP`. Same bolt, two spellings, two units — a box of 100 at ₹930 and singles at ₹9.45, which normalise to the same ₹9.30 and ₹9.45 an each. |
| `900101` + `900103` | **Different part** | Finish is `critical`: zinc plated is not hot-dip galvanised. Nothing else differs, which is exactly the merge a text matcher makes. |
| `900104` + `900105` | **Possible substitute** | A2-70 against A4-70 is a declared substitution group. The ruling carries its condition: A4 is required in chloride or marine exposure, and the relation is not symmetric. |
| `900106` + `900107` | **Not enough information** | Neither records a usable grade — `900106` omits it, `900107` writes `PC10.9`, a surface form no dictionary declares. The system says unknown rather than guessing, and asks the steward. |
| `900108` + `900109` | **Same material**, identity tier | Same manufacturer and same part number, so identity is established without inference — even though `900109` never states the standard. |
| `900108` + `900114` | **Same material**, attribute tier | A third code for the same bolt, with no manufacturer recorded at all. The three together are one identity under three codes. |
| `900110` + `900111` | **Same material** | One says DIN 931, the other ISO 4014. The dictionary declares them equivalent, so this is not a conflict — a string comparison would call it one. |
| `900113` | Dead stock | Last issued 2023-10-09, 5 boxes of 500 held. Feeds the "no order in four years" reading. |

### `IOCL_ball_bearings_sample.csv` — SAP headers, IOCL's house style
Written in IOCL's declared style ("Verbose title case"), with raw SAP field names as headers —
`MATNR`, `MAKTX`, `MEINS`, `MENGE`, `NETPR`, `MFR`, `MFRPN`, `LABST`, `Last Goods Issue`.
All nine map at full confidence from `column_aliases.yaml`, which is the point of showing it:
nobody maps this file by hand.

| Rows | What happens | Why |
|---|---|---|
| `900201` + `900203` | **Different part** | Both are 25mm bore. One is a 6205, the other a 6305 — medium duty against heavy. Same size, not interchangeable; the trap a size-only matcher falls into. |
| `900201` + `900202` | **Same material** | `2RS / Clearance C3 / Steel Cage` against `Rubber Sealed / Clearance C-3 / Pressed Steel`, one priced per each and one per box of 50. |
| `900201` + `900204` | **Possible substitute** | C3 against CN. C3 is required where the inner ring runs hot; substituting CN there will preload the bearing and fail it early. |
| `900201` + `900205` | **Possible substitute** | 2RS against ZZ. Contact seals exclude washdown water; shields suit higher speed. Not to be substituted in a wet location. |
| `900206` + `900207` | **Not enough information** | `900206` never states internal clearance, which is identity-defining for a bearing. Routed to the steward rather than merged. |
| `900207` + `900208` | **Same material**, identity tier | Same manufacturer and part number, though `900208` writes the closure as `Shld`, which no dictionary declares, and carries a different cage. |
| `900201` + `900212` | **Same material** | `900212` records no cage at all. Cage is `informational`, so a fact only one side wrote down does not stand in the way. |
| `900210` + `900211` | **Same material** | `2RS / C4 / Machined Brass` against `Double Sealed / C-4 / Brass Cage`. |

## Two things worth saying out loud while demonstrating

- **Units are normalised at the boundary.** `BOX-100`, `BOX-50`, `BOX-500`, `DOZ` and `C` all
  resolve to a count of each, so a box of a hundred at ₹930 is compared with ₹9.45 a piece and
  not with ₹9.45 a box. Stock is normalised the same way, which is what makes a transfer
  recommendation between two organisations mean anything.
- **Unknown is an output.** `PC10.9` and `Shld` are wording the dictionaries do not declare.
  Both stay unknown rather than being guessed at, and the pairs that depend on them are put
  to a person.
