"""Work out which column holds which fact, so nobody maps a CSV by hand.

Three passes, most confident first. A suggestion always carries how it was reached, so the
screen can pre-fill confident matches and only ask about the rest.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


@dataclass
class Suggestion:
    field: str
    column: str | None
    confidence: float
    how: str
    alternatives: list[str] = field(default_factory=list)


class ColumnDetector:
    def __init__(self, spec: dict) -> None:
        self.spec = spec

    @classmethod
    def from_file(cls, path: Path) -> "ColumnDetector":
        return cls(yaml.safe_load(Path(path).read_text()))

    def detect(self, headers: list[str], kind: str = "catalogue") -> list[Suggestion]:
        aliases = self.spec[kind]
        norm = {h: _norm(h) for h in headers}
        taken: set[str] = set()
        out: list[Suggestion] = []

        # Longest field names first, so "manufacturer part number" claims its column before
        # plain "manufacturer" can take it on a substring match.
        for fieldname, entries in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
            names = [a.strip() for entry in entries for a in str(entry).split(",")]
            wanted = {_norm(n) for n in names if n}

            hit = next((h for h in headers if h not in taken and norm[h] in wanted), None)
            if hit:
                taken.add(hit)
                out.append(Suggestion(fieldname, hit, 1.0, "exact header match"))
                continue

            # Contained either way: "material_code_no" against "materialcode".
            scored = []
            for h in headers:
                if h in taken:
                    continue
                for w in wanted:
                    if len(w) < 3:
                        continue
                    if w in norm[h] or norm[h] in w:
                        scored.append((len(w) / max(len(norm[h]), len(w)), h))
                        break
            if scored:
                scored.sort(reverse=True)
                best_score, best = scored[0]
                taken.add(best)
                out.append(Suggestion(fieldname, best, round(0.55 + 0.4 * best_score, 2),
                                      "partial header match",
                                      [h for _, h in scored[1:3]]))
                continue

            out.append(Suggestion(fieldname, None, 0.0, "no column matched",
                                  [h for h in headers if h not in taken][:4]))
        return out


def preview(content: bytes, detector: ColumnDetector, kind: str = "catalogue",
            rows: int = 5) -> dict:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    sample = [row for _, row in zip(range(rows), reader)]
    suggestions = detector.detect(headers, kind)
    mapping = {s.field: s.column for s in suggestions if s.column}
    return {"headers": headers, "sample_rows": sample,
            "suggestions": suggestions, "column_map": mapping}
