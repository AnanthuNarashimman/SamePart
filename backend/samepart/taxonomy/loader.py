"""The classification backbone.

UNSPSC is a four-level code: two digits each for segment, family, class and commodity, so
31161602 is segment 31, family 3116, class 311616, commodity 31161602. Hierarchy is carried
by the code itself, which is why we index by prefix rather than by the parent-key column.

The codeset is DATA, loaded at runtime. Swapping it for a licensed or government-issued
codeset is a file change, not a code change. This matters: the free extract from the UN
procurement portal is licensed personal-use-only and cannot be redistributed, so a national
deployment would need its own copy.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LEVELS = ("segment", "family", "class", "commodity")


def level_of(code: str) -> str:
    c = str(code)
    if c.endswith("000000"):
        return "segment"
    if c.endswith("0000"):
        return "family"
    if c.endswith("00"):
        return "class"
    return "commodity"


def prefix_at(code: str, level: str) -> str:
    n = {"segment": 2, "family": 4, "class": 6, "commodity": 8}[level]
    return str(code)[:n].ljust(8, "0")


@dataclass(frozen=True)
class Node:
    code: str
    title: str
    level: str

    @property
    def path_codes(self) -> list[str]:
        upto = LEVELS[: LEVELS.index(self.level) + 1]
        return [prefix_at(self.code, lv) for lv in upto]


class Taxonomy:
    def __init__(self, nodes: list[Node], name: str = "UNSPSC") -> None:
        self.name = name
        self.by_code = {n.code: n for n in nodes}
        self.nodes = nodes

    @classmethod
    def from_xlsx(cls, path: Path, sheet: str = "UNSPSC") -> "Taxonomy":
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True)
        nodes = []
        for row in list(wb[sheet].iter_rows(values_only=True))[1:]:
            code, title = row[2], row[3]
            if not code or len(str(code)) != 8 or not title:
                continue
            code = str(code)
            nodes.append(Node(code, str(title).strip(), level_of(code)))
        return cls(nodes)

    def children(self, code: str) -> list[Node]:
        parent_level = level_of(code)
        if parent_level == "commodity":
            return []
        child_level = LEVELS[LEVELS.index(parent_level) + 1]
        n = {"family": 2, "class": 4, "commodity": 6}[child_level]
        stem = str(code)[:n]
        return [x for x in self.nodes
                if x.level == child_level and x.code.startswith(stem)]

    def path(self, code: str) -> list[Node]:
        return [self.by_code[c] for c in Node(code, "", level_of(code)).path_codes
                if c in self.by_code]

    def label(self, code: str, sep: str = " > ") -> str:
        return sep.join(n.title for n in self.path(code))

    def at_level(self, level: str) -> list[Node]:
        return [n for n in self.nodes if n.level == level]

    def counts(self) -> dict[str, int]:
        return {lv: len(self.at_level(lv)) for lv in LEVELS}
