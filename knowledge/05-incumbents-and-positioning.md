# Who already sells this, and how we position honestly

Our plan currently names no incumbent. "How is this different from what already exists" is
a certain question, and there are at least three real answers we need to be ready for.

## SAP MDG-M and Information Steward — the baseline every CPSE already owns

Built into S/4HANA. Two-level dedup: exact-field match on description, record ID and
manufacturer part number, then fuzzy scoring on overlapping attributes and UoM, surfacing
candidates for human review before creation.

**The opening we have:** SAP's own Information Steward is documented as harder to apply to
**material** master than to customer or vendor master, because characteristic data is not
held in one flat table.

Nearly every major Indian CPSE — ONGC, IOCL, BHEL, SAIL, Coal India, NTPC — already runs
SAP. This is the tool they own and evidently under-use.

[SAP Help Portal](https://help.sap.com/docs/SAP_MASTER_DATA_GOVERNANCE/e605401fa254458cbe47498c514d42ce/c9c166fecde94d968db4faa1c9eab709.html)

## PiLog Group — the closest existing product to what we are proposing

- Established 1996, with an Indian entity (PiLog India Pvt Ltd)
- Products explicitly conform to **ISO 8000-110:2009**
- Sells "PiLog's Material Master Taxonomy for SAP Master Data Governance" as an SAP-listed
  partner product

This is the closest existing commercial "Indian material code harmonization on SAP MDG"
offering. We must acknowledge it. No ROI numbers or named PSU case studies found.

## Verdantis — the best published numbers

- Indian entity in Bangalore, incorporated 2013, roughly $15M revenue (2025)
- Claims 95%+ duplicate elimination via "Auto Dups AI", 10x throughput versus manual,
  250+ projects and 150M+ records processed
- Case studies: North American steel producer, 15% dupes across 300k records, $37.5M
  savings; beverage multinational, 22% duplicate SKUs across 440k items, $8.7M savings
- **All case studies are anonymised. No named Indian CPSE client found.**

## Others, briefly

- **Prospecta MDO** — explicitly targets mining and oil & gas; case-study index unverifiable
- **Stibo Systems, Informatica MDM, Reltio, Precisely EnterWorks** — general enterprise
  MDM/PIM, not MRO-specialised
- **Datactics** — UK, financial services and public sector focus
- **Vroozi** — procure-to-pay, does **not** actually compete in this space
- **"Simplifed"** — could not be verified as a real vendor; likely a name error

## Our honest differentiator

**Not** "we do matching." Everyone does matching.

The line is: **cross-organisation harmonization with evidence and refusal**, where the
incumbents do single-enterprise cleansing engagements.

Three things we do that the incumbent framing does not cover:

1. **Multi-organisation by design.** Incumbents clean one company's master. The problem
   statement is about reconciling identity *between* organisations that will never share an
   ERP, with the political constraint that nobody's existing codes get overwritten.
2. **Refusal as a first-class output.** The system says "insufficient evidence" and asks for
   the missing attribute, instead of forcing a binary. In a refinery, a wrong merge is a
   safety incident, not a data-quality ticket.
3. **Evidence per field, not a similarity score.** A reviewer sees which words in which
   description justified each extracted value, and which deterministic gate fired.

## Published ROI numbers we can borrow, with caveats

| Claim | Source | Strength |
|---|---|---|
| ₹12,743 crore losses, SAIL, 7 years | CAG Report No. 10 of 2025 | **Primary, audited, strongest we have** |
| 10–15% off annual indirect spend | McKinsey (retail, not industrial) | Primary consultancy |
| One retailer: 11% reduction, >$500M TCO savings | McKinsey | Primary consultancy |
| 20% inventory reduction, best-in-class manufacturers | Aberdeen, cited secondhand only | Weak, original not locatable |
| 17.9% average savings buying on-catalogue vs off | Aberdeen-sourced, secondary | Weak |
| ₹65.46 crore avoidable accumulation, Indian Railways safety items | CAG Report No. 29 of 2015 | Primary, audited |

No hard numbers found for Coal India, BHEL or NTPC material-master duplication specifically.
