"""What the matcher actually gets right, measured against the labels.

Every number this project has quoted so far was computed once, in conversation, and then
copied into prose. That is not a benchmark — it is an anecdote with a decimal point. This
recomputes all of them from the database on demand, so a claim can be checked rather than
believed, and so a regression fails a build instead of surviving into a demo.

Three things are deliberately kept apart, because conflating them is how entity-resolution
projects flatter themselves:

  Retrieval    did the candidate pair ever get generated? A pair blocking never surfaces is
               a miss no amount of downstream cleverness recovers, and measuring recall only
               over generated candidates hides exactly that failure.
  Decision     given the pair, did the cascade call it correctly? This is the matcher.
  Outcome      after approvals, are the final clusters right? This is the system.

A false merge and a false separation are both errors and are never averaged together. Merging
two different materials puts the wrong part in a pipeline; failing to merge two identical ones
leaves a duplicate. The first is the one that gets someone hurt, so it is reported on its own.
"""
from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import select

from samepart.db.models import (
    ApprovedMapping, CandidateMatch, ExtractedAttribute, SourceRecord,
)

Pair = tuple[int, int]


def _pair(a: int, b: int) -> Pair:
    """Order-independent, so a pair is the same pair whichever way round it was stored."""
    return (a, b) if a < b else (b, a)


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn}


def _bcubed(predicted: dict[int, str], truth: dict[int, str]) -> dict[str, float]:
    """B-cubed precision and recall, averaged per record rather than per cluster.

    The right metric for this problem and, as far as the competitor repos show, one nobody
    else in the field is using. Pairwise metrics let one enormous wrong cluster dominate the
    score; B-cubed asks of each record separately "of the records grouped with me, what share
    belong with me", which is the question a data steward actually has.
    """
    by_pred: dict[str, set[int]] = defaultdict(set)
    by_true: dict[str, set[int]] = defaultdict(set)
    for rid, cid in predicted.items():
        by_pred[cid].add(rid)
    for rid, cid in truth.items():
        by_true[cid].add(rid)

    ps, rs = [], []
    for rid in truth:
        p_cluster = by_pred.get(predicted.get(rid, f"__singleton_{rid}"), {rid})
        t_cluster = by_true[truth[rid]]
        shared = len(p_cluster & t_cluster)
        ps.append(shared / len(p_cluster))
        rs.append(shared / len(t_cluster))

    precision = sum(ps) / len(ps) if ps else 0.0
    recall = sum(rs) / len(rs) if rs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


@dataclass
class Report:
    records: int = 0
    labelled: int = 0
    true_pairs: int = 0
    comparisons: int = 0

    retrieval: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    outcome: dict = field(default_factory=dict)
    hard_negatives: dict = field(default_factory=dict)
    price_flag: dict = field(default_factory=dict)
    tiers: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "records": self.records, "labelled": self.labelled,
            "true_pairs": self.true_pairs, "comparisons": self.comparisons,
            "retrieval": self.retrieval, "decision": self.decision,
            "outcome": self.outcome, "hard_negatives": self.hard_negatives,
            "price_flag": self.price_flag, "tiers": self.tiers, "notes": self.notes,
        }

    def flat(self) -> dict[str, float]:
        """Every scalar as `section.metric`, which is what thresholds are written against."""
        out: dict[str, float] = {}
        for section in ("retrieval", "decision", "outcome", "hard_negatives",
                        "price_flag", "tiers"):
            for k, v in getattr(self, section).items():
                if isinstance(v, (int, float)):
                    out[f"{section}.{k}"] = v
                elif isinstance(v, dict):
                    for k2, v2 in v.items():
                        if isinstance(v2, (int, float)):
                            out[f"{section}.{k}.{k2}"] = v2
        return out


def evaluate(db, *, family: str | None = None) -> Report:
    r = Report()

    records = list(db.scalars(select(SourceRecord)))
    if family:
        records = [x for x in records if x.family == family]
    r.records = len(records)

    # Hand-authored walkthrough fixtures carry their own made-up identities. One of them is,
    # by design, a real bolt that the generator also produced, so scoring it counts a correct
    # merge as a false one. They are for the demo, not the benchmark, and are set aside here
    # with the count printed rather than silently.
    demo = [x for x in records if x.truth_identity and x.truth_identity.startswith("DEMO-")]
    truth = {x.id: x.truth_identity for x in records
             if x.truth_identity and not x.truth_identity.startswith("DEMO-")}
    r.labelled = len(truth)
    if demo:
        r.notes.append(f"{len(demo)} hand-authored demo fixtures excluded from the labelled set.")
    if not truth:
        r.notes.append("No labelled records. Run `cli seed`, which writes truth_identity.")
        return r

    ids = set(truth)
    r.comparisons = math.comb(len(ids), 2)

    # Every pair that IS the same material, whether or not anything ever proposed it.
    by_identity: dict[str, list[int]] = defaultdict(list)
    for rid, tid in truth.items():
        by_identity[tid].append(rid)
    true_pairs: set[Pair] = set()
    for group in by_identity.values():
        for a, b in itertools.combinations(sorted(group), 2):
            true_pairs.add((a, b))
    r.true_pairs = len(true_pairs)

    attributes: dict[int, dict[str, str | None]] = defaultdict(dict)
    for a in db.scalars(select(ExtractedAttribute)):
        if a.record_id in ids:
            attributes[a.record_id][a.key] = _attr_value(a)

    matches = [m for m in db.scalars(select(CandidateMatch))
               if m.a_id in ids and m.b_id in ids]
    candidates: set[Pair] = {_pair(m.a_id, m.b_id) for m in matches}

    # ── Retrieval ───────────────────────────────────────────────────────────────────────
    # Pairs Completeness and Reduction Ratio, the standard blocking pair (Papadakis et al.,
    # ACM CSUR 2020). They trade off: a blocking scheme can always buy completeness by
    # generating more pairs, so neither number means anything alone.
    found = len(true_pairs & candidates)
    r.retrieval = {
        "candidate_pairs": len(candidates),
        "pairs_completeness": round(found / len(true_pairs), 4) if true_pairs else 0.0,
        "reduction_ratio": round(1 - len(candidates) / r.comparisons, 4) if r.comparisons else 0.0,
        "true_pairs_missed": len(true_pairs) - found,
    }

    # ── Decision ────────────────────────────────────────────────────────────────────────
    said_same = {_pair(m.a_id, m.b_id) for m in matches if m.verdict == "same_material"}
    said_diff = {_pair(m.a_id, m.b_id) for m in matches if m.verdict == "different"}
    abstained = {_pair(m.a_id, m.b_id) for m in matches if m.verdict == "insufficient_evidence"}
    alternative = {_pair(m.a_id, m.b_id) for m in matches if m.verdict == "possible_alternative"}

    # Some labelled-different pairs carry no disagreeing evidence at all: every attribute
    # either agrees or is missing on one side. Nothing could separate those, so counting them
    # as matcher errors measures the labels, not the matcher. They are reported on their own
    # as a ceiling. This is not an excuse -- a pair only qualifies when NO stated attribute
    # disagrees, which is a strict test, and the count is printed whether it flatters us or
    # not.
    # Declared equivalences (ISO 4014 and DIN 931; ASME B16.20 and API 601) are agreement,
    # not conflict: two records stating them are saying the same thing in two vocabularies.
    # Without this the count blames "standard" for merges whose real cause is elsewhere.
    equivalent = _equivalences()
    family_of = {x.id: x.family for x in records}
    indistinguishable = {p for p in (said_same - true_pairs)
                         if not _has_conflict(p, attributes, equivalent.get(family_of[p[0]], {}))}

    tp = len(said_same & true_pairs)
    fp = len(said_same - true_pairs)
    # Recall is measured against every true pair, including ones retrieval never surfaced.
    # Scoring only the pairs that reached the cascade would quietly forgive blocking misses.
    fn = len(true_pairs) - tp

    r.decision = {
        "pairwise": _prf(tp, fp, fn),
        "false_merges": fp,
        "false_merge_rate": round(fp / len(said_same), 4) if said_same else 0.0,
        "false_merges_with_conflicting_evidence": fp - len(indistinguishable),
        "indistinguishable_pairs": len(indistinguishable),
        "false_separations": len(said_diff & true_pairs),
        "false_separation_rate": round(len(said_diff & true_pairs) / len(true_pairs), 4)
                                 if true_pairs else 0.0,
        "abstained": len(abstained),
        "abstention_rate": round(len(abstained) / len(matches), 4) if matches else 0.0,
        "possible_alternative": len(alternative),
        "decided_pairs": len(matches),
    }

    tier = Counter(m.decided_by or "undecided" for m in matches)
    without_model = sum(n for t, n in tier.items() if t != "model")
    r.tiers = {
        "by_tier": dict(sorted(tier.items(), key=lambda kv: -kv[1])),
        "share_without_a_model": round(without_model / len(matches), 4) if matches else 0.0,
    }

    # ── Outcome ─────────────────────────────────────────────────────────────────────────
    predicted_cluster = {m.record_id: m.canonical_id
                         for m in db.scalars(select(ApprovedMapping))
                         if m.record_id in ids}
    r.outcome = {
        "records_mapped": len(predicted_cluster),
        "clusters": len(set(predicted_cluster.values())),
        "true_clusters": len(by_identity),
        "bcubed": _bcubed(predicted_cluster, truth),
    }

    # A cluster is pure when every record in it shares one true identity. Impure clusters are
    # the ones a person would have to unpick, so they are counted, not averaged away.
    grouped: dict[str, set[str]] = defaultdict(set)
    for rid, cid in predicted_cluster.items():
        grouped[cid].add(truth[rid])
    impure = [cid for cid, tids in grouped.items() if len(tids) > 1]
    r.outcome["impure_clusters"] = len(impure)
    r.outcome["cluster_purity"] = round(1 - len(impure) / len(grouped), 4) if grouped else 0.0

    # ── Hard negatives ──────────────────────────────────────────────────────────────────
    # Pairs that look alike enough to be proposed but are genuinely different materials. These
    # are the pairs a naive text matcher merges, so performance here is the whole argument for
    # typed attributes and conflict gates. Derived rather than hand-built: any candidate pair
    # whose records carry different true identities already qualifies.
    hard = candidates - true_pairs
    hard_same = len(hard & said_same)
    r.hard_negatives = {
        "pairs": len(hard),
        "wrongly_merged": hard_same,
        "correctly_separated": len(hard & said_diff),
        "sent_to_a_person": len(hard & (abstained | alternative)),
        "false_merge_rate": round(hard_same / len(hard), 4) if hard else 0.0,
    }

    # ── Price variance as an independent check ──────────────────────────────────────────
    # Not a matching signal — a second opinion from a different kind of evidence. If a cluster
    # is wrong, the prices inside it tend to disagree, and that is derived from procurement
    # history rather than from the descriptions the matcher already read. Reported as
    # screening performance, never as proof.
    spreads: dict[str, float] = {}
    for cid, rids in _cluster_records(predicted_cluster).items():
        prices = [x.unit_price_base for x in records
                  if x.id in rids and x.unit_price_base and x.unit_price_base > 0]
        if len(prices) >= 2:
            spreads[cid] = max(prices) / min(prices)
    if spreads:
        threshold = _flag_threshold(list(spreads.values()))
        flagged = {cid for cid, s in spreads.items() if s >= threshold}
        impure_set = set(impure)
        scored = set(spreads)
        r.price_flag = {
            "threshold": round(threshold, 3),
            "clusters_scored": len(scored),
            "flagged": len(flagged),
            **_prf(
                tp=len(flagged & impure_set),
                fp=len(flagged - impure_set),
                fn=len((impure_set & scored) - flagged),
            ),
        }
    else:
        r.notes.append("No cluster had two priced records; price-variance check skipped.")

    unknown = db.scalar(select(ExtractedAttribute.id)) is not None
    if not unknown:
        r.notes.append("No extracted attributes found; extraction was not run.")
    return r


def _attr_value(a: ExtractedAttribute) -> str | None:
    """None where the record did not state the fact, so silence never reads as disagreement."""
    if a.status in ("unknown", "unresolvable"):
        return None
    if a.value_text is not None:
        return a.value_text
    return str(a.value_number) if a.value_number is not None else None


def _has_conflict(pair: Pair, attributes: dict[int, dict[str, str | None]],
                  equivalent: dict[str, dict[str, str]] | None = None) -> bool:
    """True when some attribute is stated on both records and the two values differ,
    after mapping each value through the family's declared equivalences."""
    a, b = attributes.get(pair[0], {}), attributes.get(pair[1], {})
    eq = equivalent or {}

    def canon(k: str, v: str) -> str:
        return eq.get(k, {}).get(v, v)

    return any(a.get(k) is not None and b.get(k) is not None
               and canon(k, a[k]) != canon(k, b[k])
               for k in set(a) | set(b))


def _equivalences() -> dict[str, dict[str, dict[str, str]]]:
    """family -> attribute -> value -> canonical member, from `relation: equivalent` groups."""
    from samepart.api.deps import dictionary

    out: dict[str, dict[str, dict[str, str]]] = {}
    for name, fam in dictionary().families.items():
        for g in fam.substitution_groups:
            if getattr(g.relation, "value", g.relation) != "equivalent" or len(g.members) < 2:
                continue
            out.setdefault(name, {}).setdefault(g.attribute, {}).update(
                {m: g.members[0] for m in g.members})
    return out


def _cluster_records(mapping: dict[int, str]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = defaultdict(set)
    for rid, cid in mapping.items():
        out[cid].add(rid)
    return out


def _flag_threshold(spreads: Iterable[float]) -> float:
    """1.5x the median spread, so the bar adapts to the catalogue rather than being invented."""
    xs = sorted(spreads)
    mid = xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2
    return round(mid * 1.5, 3)
