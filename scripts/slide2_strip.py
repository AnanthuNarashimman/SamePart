"""Four measured figures for the idea slide, read from the same places the tables read them.

The slide is the first thing a judge reads and often the only thing they remember, and until
now the measurements did not appear until slide 4. This puts the four that matter beside the
claims, in the shape of the product's own dashboard tiles, and takes each from the harness or
the export service so the strip cannot say something the system would not.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from samepart.api.deps import dictionary  # noqa: E402
from samepart.db.session import session_scope  # noqa: E402
from samepart.evaluation.harness import evaluate  # noqa: E402
from samepart.services.live import LiveExport  # noqa: E402

OUT = ROOT / "data" / "generated" / "charts" / "figures_strip.png"
INK, INK_2, INK_3, RULE, SURFACE = "#0b0b0b", "#52514e", "#a3a29c", "#d9d8d3", "#ffffff"
plt.rcParams.update({"font.family": ["Arial", "Helvetica", "DejaVu Sans"],
                     "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def figures() -> list[tuple[str, str, str]]:
    with session_scope() as db:
        r = evaluate(db)
    altered = LiveExport(dictionary()).migration_preview().fields_altered
    model_calls = round((1 - r.tiers["share_without_a_model"]) * r.decision["decided_pairs"])
    return [
        (f"{r.records:,} → {r.outcome['clusters']:,}", "source codes to national identities",
         "measured"),
        (f"{r.decision['pairwise']['precision'] * 100:.1f}%",
         f"precision on {r.decision['decided_pairs']:,} candidate pairs", "measured"),
        (f"{model_calls:,}", "model calls needed to decide them", "measured"),
        (f"{altered:,}", "existing fields altered in a CPSE master", "by construction"),
    ]


def main() -> int:
    items = figures()
    fig = plt.figure(figsize=(6.35, 1.62), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    # Columns sized to what they hold: an arrow expression and a long label need more room
    # than a lone zero, and equal columns put the first figure into the second's space.
    weights = [1.32, 0.92, 0.96, 1.20]
    total = sum(weights)
    x0 = 0.0
    for i, ((value, label, kind), w) in enumerate(zip(items, weights)):
        if i:
            ax.plot([x0, x0], [0.14, 0.86], color=RULE, linewidth=0.7)
        ax.text(x0 + 0.018, 0.66, value, fontsize=17, fontweight="bold", color=INK, ha="left",
                va="center")
        ax.text(x0 + 0.018, 0.34, textwrap.fill(label, 24), fontsize=6.9, color=INK_2, ha="left",
                va="center", linespacing=1.25)
        ax.text(x0 + 0.018, 0.11, kind, fontsize=5.8, color=INK_3, ha="left", va="center")
        x0 += w / total
    ax.plot([0, 1], [0.97, 0.97], color=RULE, linewidth=0.7)
    fig.savefig(OUT)
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
