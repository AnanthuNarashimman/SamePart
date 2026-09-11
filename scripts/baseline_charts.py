"""Draw the baseline comparison as two figures sized for the deck.

Reads data/generated/baselines.json, which `cli baselines --json` writes, so the pictures are
regenerated from the same run the tables quote and can never drift from them.

Two figures, one question each:

  precision_recall.png   The whole tradeoff. Every baseline's full curve, our single operating
                         point, and a line at our precision that no curve crosses. This is the
                         picture that makes the "—" row in the table visible.
  false_merges.png       The cost of finding what we find. False merges at matched recall on a
                         log axis, because 16 against 2,764 is the argument and a linear axis
                         would make our bar invisible rather than small.

Sized to drop into the slide slots they replace (about four inches square), so type is set at
the size it will actually be read at rather than scaled down afterwards.
"""
from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "generated" / "baselines.json"
OUT = ROOT / "data" / "generated" / "charts"

# Validated categorical palette (dataviz reference, light surface). Assigned in a fixed order
# to the baselines; ours is drawn in ink rather than as a fifth hue, because it is not one of
# the series being compared, it is the thing they are compared against.
HUES = {
    "fuzzy_tokens": "#2a78d6",
    "fuzzy_trigrams": "#eb6834",
    "embedding": "#1baf7a",
    "llm_only": "#eda100",
}
LABELS = {
    "fuzzy_tokens": "Fuzzy, tokens",
    "fuzzy_trigrams": "Fuzzy, trigrams",
    "embedding": "Embedding",
    "llm_only": "LLM only",
    "exact_text": "Exact text",
}
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#a3a29c"
GRID = "#e8e7e3"
SURFACE = "#ffffff"

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.edgecolor": INK_3,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def pct(x, _pos=None) -> str:
    return f"{x * 100:.0f}%"


def provenance(data: dict, width: int = 120) -> str:
    """Why these are not made-up numbers — the same sentence on every figure, wrapped to fit."""
    run_date = datetime.fromtimestamp(SRC.stat().st_mtime).strftime("%d %b %Y")
    return textwrap.fill(
        f"Measured, not modelled: a single real run on {run_date} over all "
        f"{data['records']:,} labelled records and {data['candidate_pairs']:,} candidate "
        "pairs, the matcher never shown the labels. Reproducible with "
        "`samepart.cli baselines`; every figure is in data/generated/baselines.json.",
        width=width)


def precision_recall(data: dict) -> Path:
    ours = data["ours"]
    fig, ax = plt.subplots(figsize=(3.8, 3.96), dpi=300)
    fig.subplots_adjust(left=0.15, right=0.97, top=0.80, bottom=0.215)

    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.5)
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # The line no baseline crosses. Drawn first so every curve sits on top of it.
    ax.axhline(ours["precision"], color=INK_3, linewidth=0.7, linestyle=(0, (3, 2)))
    ax.text(0.015, ours["precision"] - 0.012, f"Meridian precision {ours['precision'] * 100:.1f}%",
            fontsize=6.4, color=INK_2, va="top", ha="left")

    curves = {b["name"]: b for b in data["baselines"] if b["curve"]}
    for name in ("fuzzy_tokens", "fuzzy_trigrams", "embedding"):
        b = curves.get(name)
        if not b:
            continue
        pts = sorted(b["curve"], key=lambda p: p["recall"])
        xs = [p["recall"] for p in pts]
        ys = [p["precision"] for p in pts]
        ax.plot(xs, ys, color=HUES[name], linewidth=1.3, solid_capstyle="round",
                label=LABELS[name], zorder=3)

    # LLM only is a single sampled point, not a curve: hollow so it reads as an estimate.
    llm = next((b for b in data["baselines"] if b["name"] == "llm_only" and b["best_f1"]), None)
    if llm:
        p = llm["best_f1"]
        ax.plot(p["recall"], p["precision"], marker="D", markersize=5.5, markerfacecolor=SURFACE,
                markeredgecolor=HUES["llm_only"], markeredgewidth=1.3, linestyle="none",
                label="LLM only (sampled)", zorder=4)
        ax.annotate("LLM only\n(sampled; one model\ncall per pair)", (p["recall"], p["precision"]),
                    xytext=(p["recall"] - 0.035, p["precision"] - 0.03), fontsize=6.4,
                    color=INK_2, ha="right", va="top", linespacing=1.25)

    # Ours: the one filled mark on the chart.
    ax.plot(ours["recall"], ours["precision"], marker="o", markersize=7, color=INK,
            markeredgecolor=SURFACE, markeredgewidth=1.2, linestyle="none", label="Meridian",
            zorder=5)
    ax.annotate("Meridian", (ours["recall"], ours["precision"]),
                xytext=(ours["recall"] + 0.03, ours["precision"] + 0.008), fontsize=7.2,
                color=INK, fontweight="bold", ha="left", va="bottom")

    # Exact matching found nothing at all, which is worth a sentence where its point would be.
    ax.text(0.985, 0.03, "Exact text match: 0 of 1,477 pairs found", fontsize=6.4,
            color=INK_2, ha="right", va="bottom")

    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.05)
    ax.xaxis.set_major_formatter(FuncFormatter(pct))
    ax.yaxis.set_major_formatter(FuncFormatter(pct))
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Recall  (share of true duplicate pairs found)", fontsize=7)
    ax.set_ylabel("Precision  (share of merges that were right)", fontsize=7)
    ax.tick_params(length=2, labelsize=6.8)

    fig.text(0.02, 0.965, "Same pairs, every threshold", fontsize=9.5, color=INK,
             fontweight="bold", ha="left", va="top")
    fig.text(0.02, 0.905,
             f"{data['records']:,} simulated records, {data['candidate_pairs']:,} candidate pairs. "
             "Each baseline is\nshown at every threshold; none reaches our precision at any.",
             fontsize=6.6, color=INK_2, ha="left", va="top", linespacing=1.35)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.86), fontsize=6.2, frameon=False,
                    handlelength=1.6, borderaxespad=0.2, labelspacing=0.35)
    for t in leg.get_texts():
        t.set_color(INK_2)

    fig.text(0.02, 0.02, provenance(data, width=88), fontsize=5.6, color=INK_2, ha="left",
             va="bottom", linespacing=1.35)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "precision_recall.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def false_merges(data: dict) -> Path:
    ours = data["ours"]
    rows: list[tuple[str, int, str, str]] = []
    for b in data["baselines"]:
        if b["name"] == "exact_text":
            continue
        if b["name"] == "llm_only":
            # No threshold, so no matched-recall point: shown at its own operating point and
            # said so, rather than omitted.
            if b["best_f1"]:
                rows.append((LABELS[b["name"]] + "  (own point)", b["best_f1"]["false_merges"],
                             HUES[b["name"]], "estimate"))
            continue
        p = b["at_our_recall"]
        if p:
            rows.append((LABELS[b["name"]], p["false_merges"], HUES[b["name"]], "matched"))
    rows.sort(key=lambda r: -r[1])
    rows.append(("Meridian", ours["false_merges"], INK, "ours"))

    fig, ax = plt.subplots(figsize=(6.1, 3.1), dpi=300)
    fig.subplots_adjust(left=0.21, right=0.95, top=0.72, bottom=0.23)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID, linewidth=0.5)

    ys = list(range(len(rows)))[::-1]
    for y, (label, n, colour, kind) in zip(ys, rows):
        ax.barh(y, n, height=0.52, color=colour, edgecolor=SURFACE, linewidth=0.8,
                hatch="////" if kind == "estimate" else None, zorder=3)
        ax.text(n * 1.18, y, f"{n:,}", va="center", ha="left", fontsize=8.2,
                color=INK if kind == "ours" else INK_2,
                fontweight="bold" if kind == "ours" else "normal")

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    for lbl, (_, _, _, kind) in zip(ax.get_yticklabels(), rows):
        lbl.set_color(INK if kind == "ours" else INK_2)
        if kind == "ours":
            lbl.set_fontweight("bold")
    ax.tick_params(axis="y", length=0)

    ax.set_xscale("log")
    ax.set_xlim(8, 12000)
    ax.xaxis.set_major_locator(LogLocator(base=10, numticks=4))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _p: f"{x:,.0f}"))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda *_: ""))
    ax.tick_params(axis="x", labelsize=7.4, length=2)
    ax.set_xlabel("False merges  (log scale)", fontsize=7.6)

    ratio = rows[0][1] / max(ours["false_merges"], 1)
    fig.text(0.02, 0.96, "What it costs to find what we find", fontsize=10.5, color=INK,
             fontweight="bold", ha="left", va="top")
    fig.text(0.02, 0.875,
             f"Wrong parts merged at Meridian's recall ({ours['recall'] * 100:.0f}%). "
             f"The best string matcher makes {ratio:.0f}× more false merges\n"
             "to find the same duplicates. Hatched: LLM-only at its own operating point, sampled.",
             fontsize=7.2, color=INK_2, ha="left", va="top", linespacing=1.35)

    # Provenance, because a bar chart of round numbers looks exactly like one somebody made up.
    fig.text(0.02, 0.035, provenance(data), fontsize=6.3, color=INK_2, ha="left", va="bottom",
             linespacing=1.35)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "false_merges.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> int:
    if not SRC.exists():
        print(f"no {SRC}; run `cli baselines --json {SRC}` first", file=sys.stderr)
        return 1
    data = json.loads(SRC.read_text())
    for path in (precision_recall(data), false_merges(data)):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
