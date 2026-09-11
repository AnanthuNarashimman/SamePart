"""Draw one real identity converging, and one real near-miss refused, for the deck.

The idea slide used to open with a decorative arch. The checklist's point (items 6, 7 and 37)
was that the slide should open with the problem itself: several catalogues describing one
material in several house styles, and the system knowing both when those are the same part
and — the harder half — when a near-identical description is not.

Everything drawn here is read from the seeded database, not typed in. The identity, the four
source descriptions, the national code and the two refusals are whatever the matcher actually
decided, so the picture cannot say anything the product would not.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib
from sqlalchemy import select

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from samepart.db.models import (  # noqa: E402
    ApprovedMapping, CandidateMatch, Organisation, SourceRecord,
)
from samepart.db.session import session_scope  # noqa: E402

OUT = ROOT / "data" / "generated" / "charts" / "convergence.png"
IDENTITY = sys.argv[1] if len(sys.argv) > 1 else "IN-0000238-6"

# Same validated hues as the baseline charts, in the order the product uses for its CPSEs.
ORG_HUE = {"BPCL": "#2a78d6", "CPCL": "#eb6834", "IOCL": "#1baf7a", "NTPC": "#eda100"}
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#a3a29c"
RULE, SURFACE = "#d9d8d3", "#ffffff"
REFUSE = "#b3261e"
MONO = ["Menlo", "DejaVu Sans Mono", "Courier New"]

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def load():
    with session_scope() as db:
        orgs = {o.id: o.code for o in db.scalars(select(Organisation))}
        members = [m.record_id for m in db.scalars(select(ApprovedMapping))
                   if m.canonical_id == IDENTITY]
        recs = [db.get(SourceRecord, rid) for rid in members]
        # One description per CPSE, so the picture is about house styles rather than volume.
        by_org: dict[str, SourceRecord] = {}
        for r in sorted(recs, key=lambda r: (orgs[r.org_id], -len(r.raw_description))):
            by_org.setdefault(orgs[r.org_id], r)
        sources = [(code, r.source_code, r.raw_description) for code, r in sorted(by_org.items())]

        # The refusals: candidate pairs that crossed this identity's boundary and were not
        # merged. One of each kind, preferring the same house style as a merged member so the
        # near-miss is visibly near.
        member_ids = set(members)
        refused: dict[str, tuple[str, str, str]] = {}
        for m in db.scalars(select(CandidateMatch)):
            if (m.a_id in member_ids) == (m.b_id in member_ids):
                continue
            if m.verdict not in ("different", "possible_alternative"):
                continue
            other = db.get(SourceRecord, m.b_id if m.a_id in member_ids else m.a_id)
            if other.org_id in {r.org_id for r in recs} and m.verdict not in refused:
                refused[m.verdict] = (orgs[other.org_id], other.source_code, other.raw_description)

        full = IDENTITY
        try:
            # The printable form carries the classification prefix and is derived on the way
            # out, exactly as the registry does it; the stored identity never changes.
            from samepart.api.deps import dictionary
            from samepart.pipeline.registry import national_code
            cls = dictionary().family(recs[0].family).classification
            code = getattr(cls, "code", None) or (cls.get("code") if isinstance(cls, dict) else None)
            full = national_code(IDENTITY, code)
        except Exception as exc:
            print(f"full code not composed: {exc!r}", file=sys.stderr)
        return sources, refused, full, recs[0].family


def tidy(desc: str, width: int) -> str:
    """Collapsed whitespace, wrapped to the box rather than to the figure edge."""
    return textwrap.fill(" ".join(desc.split()), width=width)


def box(ax, x, y, w, h, *, edge, fill=SURFACE, lw=0.8, style="round,pad=0.008,rounding_size=0.012",
        dashed=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=lw, edgecolor=edge,
                       facecolor=fill, linestyle=(0, (3, 2)) if dashed else "solid", zorder=2)
    ax.add_patch(p)


def chip(ax, x, y, text, colour):
    ax.text(x, y, text, fontsize=5.6, fontweight="bold", color=SURFACE, ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.6", facecolor=colour,
                      edgecolor="none"), zorder=4)


def main() -> int:
    sources, refused, full, family = load()

    fig = plt.figure(figsize=(6.88, 3.86), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── headline (checklist item 7) ────────────────────────────────────────────────────
    ax.text(0.02, 0.955, "We know when not to merge.", fontsize=12, fontweight="bold",
            color=INK, ha="left", va="top")
    ax.text(0.02, 0.875, "Similarity finds candidates. Engineering evidence establishes identity. "
            "Critical conflicts always win.", fontsize=6.6, color=INK_2, ha="left", va="top")

    # ── left: four house styles, one material ──────────────────────────────────────────
    ax.text(0.02, 0.775, "FOUR CATALOGUES, FOUR HOUSE STYLES", fontsize=5.4, color=INK_3,
            ha="left", va="bottom", fontweight="bold")
    n = len(sources)
    col_x, col_w = 0.02, 0.40
    top, bottom = 0.75, 0.06
    gap = 0.025
    h = (top - bottom - gap * (n - 1)) / n
    join_x = col_x + col_w
    mid_ys = []
    for i, (org, code, desc) in enumerate(sources):
        y = top - (i + 1) * h - i * gap
        box(ax, col_x, y, col_w, h, edge=RULE)
        chip(ax, col_x + 0.015, y + h - 0.05, org, ORG_HUE[org])
        ax.text(col_x + 0.095, y + h - 0.05, code, fontsize=5.6, color=INK_3, ha="left",
                va="center", family=MONO)
        ax.text(col_x + 0.015, y + 0.035, tidy(desc, 50), fontsize=5.7, color=INK, ha="left",
                va="bottom", family=MONO, linespacing=1.3)
        mid_ys.append(y + h / 2)

    # ── centre: the national identity ──────────────────────────────────────────────────
    id_x, id_w = 0.50, 0.245
    id_h = 0.36
    id_y = (top + bottom) / 2 - id_h / 2
    box(ax, id_x, id_y, id_w, id_h, edge=INK, lw=1.1, fill="#f5f5f2")
    ax.text(id_x + 0.015, id_y + id_h - 0.045, "ONE NATIONAL IDENTITY", fontsize=5.4,
            color=INK_3, fontweight="bold", ha="left", va="center")
    ax.text(id_x + 0.015, id_y + id_h - 0.115, full, fontsize=8.2, color=INK, fontweight="bold",
            ha="left", va="center", family=MONO)
    ax.text(id_x + 0.015, id_y + id_h - 0.19, family.replace("_", " ").upper(), fontsize=6,
            color=INK_2, ha="left", va="center")
    ax.text(id_x + 0.015, id_y + 0.10, f"{n} CPSEs · {n}-way agreement", fontsize=6,
            color=INK_2, ha="left", va="center")
    ax.text(id_x + 0.015, id_y + 0.045, "each attribute traced to its evidence span", fontsize=5.6,
            color=INK_3, ha="left", va="center")

    # Converging lines: each source to the identity box, in the source's own hue.
    for (org, _, _), y in zip(sources, mid_ys):
        ax.plot([join_x, join_x + 0.03, id_x], [y, y, id_y + id_h / 2], color=ORG_HUE[org],
                linewidth=0.9, alpha=0.9, zorder=1, solid_capstyle="round")

    # ── right: what was refused, and why ───────────────────────────────────────────────
    r_x, r_w = 0.785, 0.195
    ax.text(r_x, 0.775, "KEPT SEPARATE", fontsize=5.4, color=REFUSE, fontweight="bold",
            ha="left", va="bottom")
    kinds = [("different", "DIFFERENT", "critical attribute conflicts"),
             ("possible_alternative", "POSSIBLE ALTERNATIVE", "declared substitute, not the same")]
    r_h, r_gap = 0.30, 0.04
    r_top = 0.75
    for i, (verdict, label, why) in enumerate(kinds):
        if verdict not in refused:
            continue
        org, code, desc = refused[verdict]
        y = r_top - (i + 1) * r_h - i * r_gap
        box(ax, r_x, y, r_w, r_h, edge=REFUSE, dashed=True)
        ax.text(r_x + 0.012, y + r_h - 0.04, label, fontsize=5.4, color=REFUSE,
                fontweight="bold", ha="left", va="center")
        chip(ax, r_x + 0.012, y + r_h - 0.10, org, ORG_HUE[org])
        ax.text(r_x + 0.088, y + r_h - 0.10, code, fontsize=5.4, color=INK_3, ha="left",
                va="center", family=MONO)
        ax.text(r_x + 0.012, y + 0.075, tidy(desc, 27), fontsize=5.3, color=INK, ha="left",
                va="bottom", family=MONO, linespacing=1.3)
        ax.text(r_x + 0.012, y + 0.03, why, fontsize=5.2, color=INK_2, ha="left", va="center",
                style="italic")
        ax.plot([id_x + id_w, r_x], [id_y + id_h / 2, y + r_h / 2], color=REFUSE, linewidth=0.7,
                linestyle=(0, (3, 2)), zorder=1)

    ax.text(0.02, 0.02, "Every line above is a row from the seeded catalogue and a verdict the "
            "matcher actually returned; nothing is illustrative.", fontsize=5.2, color=INK_3,
            ha="left", va="bottom")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
