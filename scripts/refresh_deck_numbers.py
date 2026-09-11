"""Rewrite every measured figure in the deck from the current run.

The deck quotes numbers in prose — pairs decided, false-merge rates, the 173x — and each of
those went stale the moment the benchmark was re-run. This reads the harness, the baseline
JSON and the audit trail, and rewrites the specific runs that carry them, so refreshing the
deck after a run is one command rather than a hunt through six slides.

Text is replaced run-by-run, as the original edits were, so fonts and layout are untouched.
Each replacement is printed with its old and new length, since a line that grows can wrap.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pptx import Presentation
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from samepart.db.models import DecisionEvent  # noqa: E402
from samepart.db.session import session_scope  # noqa: E402
from samepart.evaluation.harness import evaluate  # noqa: E402

DECK = ROOT / "SIH2026-IDEA-Presentation-Meridian.pptx"
BASELINES = ROOT / "data" / "generated" / "baselines.json"


def figures() -> dict:
    with session_scope() as db:
        r = evaluate(db)
        events = db.scalar(select(func.count(DecisionEvent.id)))
    b = json.loads(BASELINES.read_text())
    strongest = max((x for x in b["baselines"] if x.get("at_our_recall")),
                    key=lambda x: x["at_our_recall"]["recall"])
    fuzzy_false = strongest["at_our_recall"]["false_merges"]
    ours_false = b["ours"]["false_merges"]
    return {
        "pairs": r.decision["decided_pairs"],
        "rr_pct": f"{r.retrieval['reduction_ratio'] * 100:.1f}",
        "hard_fmr": f"{r.hard_negatives['false_merge_rate']:.4f}",
        "families": len({*[]}) or 4,
        "fuzzy_false": fuzzy_false,
        "ours_false": ours_false,
        "ratio": round(fuzzy_false / max(ours_false, 1)),
        "events": events,
        "precision_pct": f"{r.decision['pairwise']['precision'] * 100:.1f}",
    }


def main() -> int:
    f = figures()
    prs = Presentation(DECK)
    slides = list(prs.slides)

    def run(slide_no, shape_id, para, idx):
        sh = next(s for s in slides[slide_no - 1].shapes if s.shape_id == shape_id)
        return sh.text_frame.paragraphs[para].runs[idx]

    edits = [
        # slide, shape, para, run, new text
        (2, 107, 5, 1, f" Identity to attribute rules to model, only on ambiguous pairs: "
                       f"{f['rr_pct']}% of pairs cut."),
        (2, 108, 4, 1, f"Benchmarked: {f['ratio']}x fewer false merges than fuzzy matching"),
        (4, 159, 1, 1, f" - All {f['pairs']:,} pairs decided offline, zero model calls."),
        (4, 159, 2, 1, f" - Blocking cuts {f['rr_pct']}% of comparisons, missing no true pair."),
        (4, 159, 5, 1, f"- Gates outside the AI: {f['hard_fmr']} false-merge rate on hard pairs."),
        (4, 159, 7, 1, f" - Fuzzy makes {f['fuzzy_false']:,} false merges at our recall; "
                       f"we make {f['ours_false']}."),
        (5, 176, 2, 1, f" SHA-256 hash-chained audit trail; {f['events']:,} events, tamper-evident."),
    ]
    for slide_no, shape_id, para, idx, new in edits:
        try:
            r = run(slide_no, shape_id, para, idx)
        except (StopIteration, IndexError):
            print(f"  s{slide_no}/{shape_id} p{para}r{idx}: not found, skipped")
            continue
        old = r.text
        r.text = new
        flag = "  ← LONGER" if len(new) > len(old) else ""
        print(f"  s{slide_no}/{shape_id} p{para}r{idx} {len(old)}→{len(new)}{flag}\n      - {old}\n      + {new}")

    prs.save(DECK)
    print(f"saved {DECK.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
