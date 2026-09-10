"""Stub services returning fixed, realistic data.

These exist so the frontend is never blocked on the pipeline. The shapes are exactly what
the live services will return, and the content is the five seeded demo cases, so what gets
built against these stubs is what gets demonstrated.

Every stub is replaced independently. Nothing here is throwaway UI work.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from samepart.api import schemas as s

_A = s.AttributeView


def _attr(key, label, value, crit, unit=None, evidence=None, status=None, method="regex"):
    return _A(
        key=key, label=label, value=value, unit=unit,
        status=s.AttributeStatus(status or ("unknown" if value is None else "extracted")),
        method=s.ExtractionMethod(method),
        evidence=evidence, confidence=None if value is None else 0.99, criticality=crit,
    )


def _bolt(rid, org, code, desc, dia, ln, grade, std, finish="PLAIN", *,
          uom="EA", qty=1.0, price=41.0, base_qty=None, grade_ev=None, short=None):
    base_qty = base_qty if base_qty is not None else qty
    return s.RecordView(
        record_id=rid, org_code=org, source_code=code, raw_description=desc,
        standardised_short=short,
        uom=uom, base_uom="EA", quantity=qty,
        unit_price=price, unit_price_base=round(price / base_qty, 2),
        attributes=[
            _attr("thread_diameter_mm", "Nominal thread diameter", dia, "critical", "mm", f"M{dia:g}"),
            _attr("length_mm", "Nominal length under head", ln, "critical", "mm", f"{ln:g}"),
            _attr("grade", "Property class or grade", grade, "critical", evidence=grade_ev or grade),
            _attr("head_type", "Head type", "HEX", "critical", evidence="HEX"),
            _attr("standard", "Governing specification", std, "major", evidence=std),
            _attr("finish", "Surface finish", finish, "informational", evidence=finish),
        ],
    )


# --- the five seeded demo cases -------------------------------------------------------
_CLEAN_A = _bolt(1, "CPCL", "CPCL-000156", "HEX BOLT M16X80  A2-70  ISO 4014  PLAIN",
                 16, 80, "A2-70", "ISO4014", price=41.00,
                 short="BOLT, HEX HEAD; M16X80; A2-70; ISO4014")
_CLEAN_B = _bolt(2, "IOCL", "IOCL-000158",
                 "Bolt, Hexagon Head, M16 x 80mm, Property Class A2-70, Conforming to ISO 4014",
                 16, 80, "A2-70", "ISO4014", uom="BOX-100", qty=1.0, price=4180.00, base_qty=100,
                 short="BOLT, HEX HEAD; M16X80; A2-70; ISO4014")
_CONFLICT_A = _bolt(3, "CPCL", "CPCL-000201", "HEX BOLT M20X100  8.8  DIN 931  HDG",
                    20, 100, "8.8", "DIN931", "HOTDIPGALVANISED", price=88.0, grade_ev="8.8")
_CONFLICT_B = _bolt(4, "NTPC", "NTPC-000167",
                    "BOLT HEX HEAD; DIA 20MM; LG 100MM; GRADE 10.9  DIN 931  HOT DIP GALVANISED",
                    20, 100, "10.9", "DIN931", "HOTDIPGALVANISED", price=102.0, grade_ev="GRADE 10.9")
_INCOMPLETE_A = _bolt(5, "CPCL", "CPCL-000210", "HEX BOLT M12X60  ISO 4017  ZINC PLATED",
                      12, 60, None, "ISO4017", "ZINCPLATED", price=22.5)
_INCOMPLETE_B = _bolt(6, "IOCL", "IOCL-000214",
                      "Bolt, Hexagon Head, M12 x 60mm, Property Class 8.8, Conforming to ISO 4017, Zinc Plated",
                      12, 60, "8.8", "ISO4017", "ZINCPLATED", price=24.1)
_ALT_A = _bolt(7, "BPCL", "BPCL-000164", "BLT HEX HD M10X40MM  SS304 A2-70  ISO4014",
               10, 40, "A2-70", "ISO4014", price=18.0, grade_ev="SS304 A2-70")
_ALT_B = _bolt(8, "NTPC", "NTPC-000171",
               "BOLT HEX HEAD; DIA 10MM; LG 40MM; GRADE A4-70  ISO 4014",
               10, 40, "A4-70", "ISO4014", price=26.5, grade_ev="GRADE A4-70")

_MATCHES: dict[int, s.MatchDetail] = {
    1: s.MatchDetail(
        id=1, verdict=s.Verdict.SAME_MATERIAL, decided_by="deterministic", score=0.98,
        gate_overrode=False, a=_CLEAN_A, b=_CLEAN_B,
        gate_firings=[s.GateFiring(
            gate_id="critical_conflict", action="none",
            message="No critical attribute disagrees.", attributes=[])],
        notes=["Both records normalise to the same base unit, so unit prices are comparable: "
               "41.00 against 41.80 per each."]),
    2: s.MatchDetail(
        id=2, verdict=s.Verdict.DIFFERENT, decided_by="gate", score=0.94,
        gate_overrode=True, a=_CONFLICT_A, b=_CONFLICT_B,
        gate_firings=[s.GateFiring(
            gate_id="critical_conflict", action="force_different",
            message="A critical attribute differs. These are not the same material.",
            attributes=["grade"], detail="grade: 8.8 vs 10.9")],
        notes=["The matcher proposed a merge on description similarity. The conflict gate "
               "overruled it."]),
    3: s.MatchDetail(
        id=3, verdict=s.Verdict.INSUFFICIENT_EVIDENCE, decided_by="gate",
        gate_overrode=True, a=_INCOMPLETE_A, b=_INCOMPLETE_B,
        gate_firings=[s.GateFiring(
            gate_id="missing_critical", action="force_insufficient",
            message="A critical attribute is unknown on at least one record. Cannot decide safely.",
            attributes=["grade"], detail="unknown on at least one record: grade")],
        notes=["Provide the property class for CPCL-000210 to resolve this pair."]),
    4: s.MatchDetail(
        id=4, verdict=s.Verdict.POSSIBLE_ALTERNATIVE, decided_by="gate",
        gate_overrode=True, a=_ALT_A, b=_ALT_B,
        gate_firings=[s.GateFiring(
            gate_id="substitution_rule", action="downgrade_to_alternative",
            message="A declared substitution covers this difference; identities stay separate.",
            attributes=["grade"], detail="grade: A2-70 vs A4-70")],
        substitution_conditions=[
            "A4 (316-type) is required where chloride or marine exposure is present. "
            "A2 (304-type) is acceptable for dry indoor service. Do not substitute A2 for "
            "A4 in coastal or offshore installations."],
        notes=["Substitution is application-dependent. These stay separate identities and "
               "are linked as alternatives."]),
}

_HEADLINES = {
    1: "Same material across two CPSEs, worded differently",
    2: "Grade conflict: 8.8 against 10.9",
    3: "Property class unknown on one record",
    4: "A2-70 against A4-70, conditional substitute",
}
_GROUP = {
    s.Verdict.INSUFFICIENT_EVIDENCE: "needs_input",
    s.Verdict.POSSIBLE_ALTERNATIVE: "possible_alternative",
    s.Verdict.SAME_MATERIAL: "same_material",
    s.Verdict.DIFFERENT: "different",
}


# The stub's curve is generated at every answer rather than at five checkpoints, for the same
# reason the live one is: the chart draws it on a numeric axis and reads the true half-way
# point off it, and a five-point sample put that point at 50 answers when it is really 26.
# The shape is interpolated between the original hand-picked checkpoints, so the fixture still
# tells the same story, just at a resolution the chart can actually use.
def _stub_curve() -> list:
    checkpoints = [(0, 0), (10, 130), (25, 221), (50, 348), (100, 508), (228, 675)]
    points = []
    for (n0, c0), (n1, c1) in zip(checkpoints, checkpoints[1:]):
        for n in range(n0 + 1, n1 + 1):
            cleared = round(c0 + (c1 - c0) * (n - n0) / (n1 - n0))
            points.append(s.CurvePoint(questions_answered=n, pairs_cleared=cleared,
                                       share_cleared=round(cleared / 689, 4)))
    return points


class StubCatalogue:
    def list_orgs(self):
        return [
            s.Org(code="CPCL", name="Chennai Petroleum Corporation Limited (simulated)", record_count=159),
            s.Org(code="IOCL", name="Indian Oil Corporation Limited (simulated)", record_count=160),
            s.Org(code="BPCL", name="Bharat Petroleum Corporation Limited (simulated)", record_count=168),
            s.Org(code="NTPC", name="NTPC Limited (simulated)", record_count=167),
        ]

    def create_org(self, code, name):
        return s.Org(code=code, name=name, record_count=0)

    def start_import(self, req, filename, content):
        rows = max(content.count(b"\n") - 1, 0)
        return s.ImportStatus(
            import_id=str(uuid.uuid4())[:8], org_code=req.org_code, status="completed",
            rows_read=rows, rows_ingested=rows, attributes_extracted=rows * 6,
            started_at=datetime.now(timezone.utc))

    def import_status(self, import_id):
        return s.ImportStatus(import_id=import_id, org_code="CPCL", status="completed",
                              rows_read=159, rows_ingested=159, attributes_extracted=954,
                              started_at=datetime.now(timezone.utc))


class StubReview:
    def queue(self, group, cursor, limit):
        counts = s.QueueCounts(needs_input=1, possible_alternative=1, same_material=1, different=1)
        items = [
            s.QueueItem(id=m.id, verdict=m.verdict, review_state=m.review_state,
                        a_description=m.a.raw_description, b_description=m.b.raw_description,
                        a_org=m.a.org_code, b_org=m.b.org_code, headline=_HEADLINES[m.id])
            for m in _MATCHES.values()
            if group in (None, "", _GROUP[m.verdict])
        ]
        order = ["needs_input", "possible_alternative", "same_material", "different"]
        items.sort(key=lambda i: order.index(_GROUP[i.verdict]))
        return s.QueuePage(counts=counts, items=items[:limit], next_cursor=None)

    def match(self, match_id):
        if match_id not in _MATCHES:
            raise KeyError(match_id)
        return _MATCHES[match_id]

    def decide(self, match_id, req):
        if match_id not in _MATCHES:
            raise KeyError(match_id)
        m = _MATCHES[match_id]
        if req.action is s.DecisionAction.APPROVE:
            return s.DecisionResult(
                match_id=match_id, new_state=s.ReviewState.APPROVED,
                canonical_id="SMP-000417", verdict=m.verdict,
                message="Mapped to SMP-000417. Both source codes are retained and unchanged.")
        if req.action is s.DecisionAction.REJECT:
            return s.DecisionResult(
                match_id=match_id, new_state=s.ReviewState.REJECTED, verdict=m.verdict,
                message="Recorded as a cannot-link constraint. These will never be merged.")
        return s.DecisionResult(
            match_id=match_id, new_state=s.ReviewState.INFO_REQUESTED, verdict=m.verdict,
            message="Information requested. The pair returns to the queue when answered.")


class StubCheck:
    def check(self, req):
        return s.CheckResult(
            verdict=s.Verdict.SAME_MATERIAL, safe_to_create=False,
            message="An equivalent material already exists as SMP-000417. "
                    "Creating a new code would duplicate it.",
            extracted=_CLEAN_A.attributes,
            candidates=[_MATCHES[1]])


class StubAnalytics:
    def summary(self):
        return s.AnalyticsSummary(
            records=654, canonical_materials=268, merged=386, conflicts_caught=41,
            duplicate_rate=0.409,
            queue_by_group=s.QueueCounts(needs_input=1, possible_alternative=1,
                                         same_material=1, different=1))

    def savings(self):
        clusters = [
            s.SavingsCluster(canonical_id="SMP-000417",
                             standardised_short="BOLT, HEX HEAD; M16X80; A2-70; ISO4014",
                             orgs=["CPCL", "IOCL", "BPCL"], price_min=41.00, price_max=43.90,
                             spread_pct=7.1, total_quantity=12400,
                             aggregation_opportunity=18104.0),
            s.SavingsCluster(canonical_id="SMP-000418",
                             standardised_short="BOLT, HEX HEAD; M20X100; 8.8; DIN931",
                             orgs=["CPCL", "NTPC", "BPCL", "IOCL"], price_min=79.20,
                             price_max=118.40, spread_pct=49.5, total_quantity=6800,
                             aggregation_opportunity=94656.0),
        ]
        return s.SavingsResult(total_opportunity=sum(c.aggregation_opportunity for c in clusters),
                               total_spend=1_284_000.0, shared_materials=len(clusters),
                               window="last 4 financial years", clusters=clusters)

    def redistribution(self, idle_days=365, limit=50):
        return s.RedistributionReport(
            idle_threshold_days=idle_days, opportunities=1, total_transferable=600.0,
            total_avoided_spend=25_080.0,
            caveats=["Stock figures in this dataset are simulated."],
            items=[s.RedistributionOpportunity(
                canonical_id="IN-0000417-6", national_code="IN-31161600-0000417-3",
                standardised_short="BOLT, HEX HEAD; M16X80; A2-70; ISO4014",
                idle_stock=600.0, annual_demand=980.0, transferable=600.0,
                unit_price_base=41.8, avoided_spend=25_080.0,
                holders=[s.StockHolder(org_code="BPCL", source_code="BPCL-000167",
                                       raw_description="BLT HEX HD M16X80MM  SS304 A2-70",
                                       stock_on_hand=6.0, stock_uom="C",
                                       stock_base_qty=600.0, idle_days=1240)],
                requesters=[s.StockRequester(org_code="CPCL", source_code="CPCL-000156",
                                             orders_in_window=4, annual_demand=980.0,
                                             unit_price_base=41.8)])])

    def cascade_breakdown(self):
        return s.CascadeBreakdown(
            total_pairs=3429, decided_without_a_model=3205, share_without_a_model=0.935,
            tiers=[s.CascadeTier(tier="identity", label="Manufacturer part number",
                                 pairs=412, share=0.12, needs_a_model=False),
                   s.CascadeTier(tier="attributes", label="Attribute agreement",
                                 pairs=1998, share=0.583, needs_a_model=False),
                   s.CascadeTier(tier="gate", label="Conflict gate",
                                 pairs=795, share=0.232, needs_a_model=False),
                   s.CascadeTier(tier="model", label="Language model",
                                 pairs=224, share=0.065, needs_a_model=True)])

    def price_spread(self, limit=12):
        return s.PriceSpreadReport(
            median_spread=1.43, flag_threshold=2.14,
            items=[s.PriceSpread(
                canonical_id="IN-0000023-1", national_code="IN-31161600-0000023-8",
                standardised_short="BOLT, HEX HEAD; M10X40; A2-70; ISO4014",
                price_min=30.79, price_max=241.75, spread=7.85, flagged=True,
                points=[s.PricePoint(org_code="BPCL", unit_price_base=30.79,
                                     quantity=8200, orders=3),
                        s.PricePoint(org_code="IOCL", unit_price_base=241.75,
                                     quantity=1400, orders=2)])])

    def stock_ageing(self, idle_days=365):
        return s.StockAgeing(
            total_records_with_stock=417, total_base_quantity=291564, idle_threshold_days=idle_days,
            buckets=[s.AgeBucket(label="under 3 months", from_days=0, to_days=90,
                                 records=52, base_quantity=18400),
                     s.AgeBucket(label="3 to 12 months", from_days=90, to_days=365,
                                 records=161, base_quantity=61200),
                     s.AgeBucket(label="1 to 2 years", from_days=365, to_days=730,
                                 records=38, base_quantity=29800),
                     s.AgeBucket(label="2 to 3 years", from_days=730, to_days=1095,
                                 records=71, base_quantity=74300),
                     s.AgeBucket(label="over 3 years", from_days=1095, to_days=None,
                                 records=95, base_quantity=107864)])

    def rationalisation(self, limit=100):
        return s.RationalisationResult(
            window="last 4 financial years", records=654, dead_codes=124,
            dead_code_rate=0.19, duplicate_codes_removable=290,
            items=[s.DeadCode(record_id=41, org_code="CPCL", source_code="CPCL-000041",
                              raw_description="HEX BOLT M8X25  8.8  DIN 933  ZINC PLATED")])

    def audit_flags(self, limit=50):
        return s.AuditFlagResult(
            median_spread_all=1.40, threshold=2.10, flagged=12,
            items=[s.AuditFlag(canonical_id="SMP-000023",
                               standardised_short="BOLT, HEX HEAD; M10X40; A2-70; ISO4014",
                               reason="Unit price varies 7.9x across buyers, against a median of 1.4x.",
                               price_spread=7.85, orgs=["IOCL", "NTPC", "BPCL"],
                               source_codes=["IOCL-000022", "NTPC-000034"])])


class StubFamilies:
    def list_families(self):
        return [s.FamilySummary(family="hex_bolt", label="Bolt, hex head",
                                attribute_count=10, gate_count=4,
                                blocking_key=["thread_diameter_mm", "length_mm"])]

    def load_family(self, yaml_text):
        return s.FamilyLoadResult(family="gasket", loaded=True, attribute_count=7, gate_count=3)


class StubQuestions:
    def questions(self, cursor, limit):
        return s.QuestionPage(
            pairs_deferred=689, questions=228, records=207,
            curve=_stub_curve(),
            items=[
                s.Question(
                    record_id=5, org_code="CPCL", source_code="CPCL-000210",
                    raw_description="HEX BOLT M12X60  ISO 4017  ZINC PLATED",
                    pairs_blocked=20,
                    missing=[s.MissingField(
                        key="grade", label="Property class or grade", criticality="critical",
                        pairs_blocked=20,
                        counterpart_values=[s.CounterpartValue(value="8.8", seen_on=17),
                                            s.CounterpartValue(value="10.9", seen_on=3)])]),
                s.Question(
                    record_id=9, org_code="BPCL", source_code="BPCL-000038",
                    raw_description="BLT HEX HD M24X100MM  DIN933",
                    pairs_blocked=16,
                    missing=[s.MissingField(
                        key="grade", label="Property class or grade", criticality="critical",
                        pairs_blocked=16,
                        counterpart_values=[s.CounterpartValue(value="A2-70", seen_on=11)]),
                        s.MissingField(
                        key="finish", label="Surface finish", criticality="critical",
                        pairs_blocked=9,
                        counterpart_values=[s.CounterpartValue(value="PLAIN", seen_on=9)])]),
            ],
            next_cursor="50")

    def unresolvable(self, record_id, req):
        return s.AnswerResult(
            record_id=record_id, applied={k: "unresolvable" for k in req.keys},
            pairs_reevaluated=12, resolved=s.QueueCounts(different=12),
            message="Recorded as unobtainable. These pairs will not be asked about again.")

    def answer(self, record_id, req):
        return s.AnswerResult(
            record_id=record_id, applied=dict(req.values), pairs_reevaluated=20,
            resolved=s.QueueCounts(same_material=14, different=6),
            message="Recorded. 20 blocked pairs re-decided.")


class StubExport:
    def cross_reference(self, org_code=None, limit=5000):
        from datetime import datetime, timezone
        return s.CrossReferenceExport(
            generated_at=datetime.now(timezone.utc), rows=654, mapped=471, dead=124,
            duplicates=290,
            items=[s.CrossReferenceRow(
                org_code="CPCL", source_code="CPCL-000156",
                national_code="IN-31161600-0000417-3", canonical_identity="IN-0000417-6",
                classification_code="31161600",
                classification_path="Manufacturing Components and Supplies > Hardware > Bolts",
                standardised_short="BOLT, HEX HEAD; M16X80; A2-70; ISO4014",
                base_uom="EA", status="active", approved_by="auto")])

    def migration_plan(self):
        from datetime import datetime, timezone
        return s.MigrationPlan(
            generated_at=datetime.now(timezone.utc), total_codes=654, keep=183,
            collapse=288, close=124, review=183, estimated_codes_removed=412,
            notes=["No CPSE material code is deleted by this plan."])

    def erp_payload(self, canonical_id):
        return {"IDOC": {"EDI_DC40": {"IDOCTYP": "MATMAS05"}}, "_note": "stub"}


class StubGovernance:
    def info(self):
        return s.GovernanceInfo(
            default_state="review_everything", policy_change_requires="administrator",
            automation_enabled=True,
            roles=[s.RoleInfo(key="steward", label="CPSE Data Steward",
                              description="Owns their own organisation's material master.",
                              permissions=["read", "answer", "decide_within_org"],
                              scope="own_organisation")])

    def audit(self, cursor=None, limit=50, actor=None, action=None):
        from datetime import datetime, timezone
        return s.AuditTrail(total=412, by_action={"approve_same": 388, "reject": 24},
                            by_actor={"auto": 388, "adi": 24},
                            items=[s.AuditEvent(id=1, at=datetime.now(timezone.utc),
                                                actor="auto", action="approve_same",
                                                canonical_id="IN-0000417-6",
                                                summary="merged into a canonical material")])

    def reverse(self, canonical_id, req):
        return s.ReverseResult(canonical_id=canonical_id, detached=req.source_codes,
                               remaining=0, dissolved=True,
                               message="No CPSE material code was altered.")
