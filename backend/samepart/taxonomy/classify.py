"""Classifying a material into the taxonomy.

Two tiers, and the first one is not machine learning at all.

1. **Declared anchor.** A family file states its class outright. Once extraction has decided
   a record is a hex bolt, its class is known, not inferred. Confidence 1.0, no model.
2. **Text classification.** For anything the first tier cannot place, the description is
   scored against node titles, walking the hierarchy top-down: segment, then family within
   the best segments, then class. Rare words carry the weight, because "bolt" is
   discriminative and "and" is not.

Accuracy is reported **per level**, which is what the literature on this task does. Blending
them into one number hides that coarse levels are easy and fine levels are hard.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from samepart.taxonomy.loader import LEVELS, Taxonomy, prefix_at

_SPLIT = re.compile(r"[^a-z0-9]+")
STOP = {"and", "or", "of", "the", "for", "with", "other", "not", "elsewhere",
        "classified", "type", "types", "misc", "miscellaneous", "supplies", "products"}


def _stem(t: str) -> str:
    """Crude singular form. The taxonomy says "Bolts", a description says "BOLT"."""
    for suffix in ("ies", "ses", "es", "s"):
        if len(t) > 4 and t.endswith(suffix):
            return t[:-3] + "y" if suffix == "ies" else t[: -len(suffix) + (1 if suffix == "ses" else 0)]
    return t


def tokens(text: str) -> list[str]:
    out = []
    for t in _SPLIT.split(str(text).lower()):
        if len(t) <= 2 or t in STOP:
            continue
        # Codes and dimensions carry no taxonomy signal and would only add noise.
        if any(ch.isdigit() for ch in t) and any(ch.isalpha() for ch in t):
            continue
        out.append(_stem(t))
    return out


@dataclass
class LevelGuess:
    level: str
    code: str
    title: str
    score: float
    runners_up: list[tuple[str, str, float]] = field(default_factory=list)


@dataclass
class Classification:
    code: str | None
    level: str | None
    path: str
    decided_by: str
    confidence: float
    per_level: list[LevelGuess] = field(default_factory=list)

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.5


class Classifier:
    """Token-IDF scoring over node titles, applied down the hierarchy."""

    def __init__(self, taxonomy: Taxonomy) -> None:
        self.tax = taxonomy
        self._tokens = {n.code: set(tokens(n.title)) for n in taxonomy.nodes}

        # A node's searchable text is its own title plus its ancestors', so "Hardware" helps
        # a bolt reach the right family even though the word never appears in a description.
        self._ctx: dict[str, set[str]] = {}
        for n in taxonomy.nodes:
            acc: set[str] = set()
            for code in n.path_codes:
                acc |= self._tokens.get(code, set())
            self._ctx[n.code] = acc

        df = Counter(t for toks in self._ctx.values() for t in toks)
        n_docs = max(len(self._ctx), 1)
        self._idf = {t: math.log(1 + n_docs / (1 + c)) for t, c in df.items()}

    def _score(self, query: set[str], code: str) -> float:
        """Cosine-style overlap weighted by rarity.

        Normalising by the query alone was wrong: a word absent from the taxonomy has an IDF
        of zero, so it cost nothing, and a description of mostly unknown codes scored a
        perfect match off one lucky common word. Dividing by both magnitudes also stops a
        node with a long inherited context from winning on a single shared token.
        """
        cand = self._ctx.get(code, set())
        shared = query & cand
        if not shared:
            return 0.0
        num = sum(self._idf.get(t, 0.0) ** 2 for t in shared)
        # Unknown query words still count, at the rarest weight, so they penalise.
        floor = max(self._idf.values()) if self._idf else 1.0
        q_mag = math.sqrt(sum(self._idf.get(t, floor) ** 2 for t in query))
        c_mag = math.sqrt(sum(self._idf.get(t, 0.0) ** 2 for t in cand))
        return num / (q_mag * c_mag) if q_mag and c_mag else 0.0

    # Segments an industrial stores catalogue can plausibly sit in. Without this, "NUT
    # HEXAGON" classifies under agricultural nut production, which is a real and well-known
    # failure of general taxonomies applied to MRO text. Scoping is what production tools do.
    MRO_SEGMENTS = ("11", "12", "13", "14", "15", "20", "21", "22", "23", "24", "25",
                    "26", "27", "30", "31", "32", "39", "40", "41", "46", "47", "48")

    def classify(self, text: str, top_n: int = 3,
                 scope: tuple[str, ...] | None = None) -> Classification:
        """Score every terminal node directly, then read the hierarchy off the winner.

        Top-down search fails on this data: a material description shares no vocabulary with
        a segment title like "Manufacturing Components and Supplies", so the walk dies at the
        first level before it can reach the word that actually matters. Scoring terminals
        against their full ancestor context sidesteps that, and the path falls out of the
        code, since UNSPSC carries its hierarchy in the digits.
        """
        query = set(tokens(text))
        if not query:
            return Classification(None, None, "", "text", 0.0)

        # Terminals are commodities where they exist, and classes where the codeset stops
        # short. 26% of classes have no commodity detail, our fasteners among them.
        with_children = {n.code[:6] for n in self.tax.at_level("commodity")}
        terminals = self.tax.at_level("commodity") + [
            n for n in self.tax.at_level("class") if n.code[:6] not in with_children]
        if scope:
            terminals = [n for n in terminals if n.code[:2] in scope]

        scored = sorted(((self._score(query, n.code), n) for n in terminals),
                        key=lambda x: -x[0])
        best_score, best = scored[0]
        if best_score <= 0:
            return Classification(None, None, "", "text", 0.0)

        guesses = []
        for level in LEVELS[: LEVELS.index(best.level) + 1]:
            code = prefix_at(best.code, level)
            node = self.tax.by_code.get(code)
            if node:
                guesses.append(LevelGuess(level=level, code=code, title=node.title,
                                          score=round(best_score, 4)))
        if guesses:
            guesses[-1].runners_up = [(n.code, n.title, round(sc, 4))
                                      for sc, n in scored[1:1 + top_n] if sc > 0]

        return Classification(
            code=best.code, level=best.level, path=self.tax.label(best.code),
            decided_by="text", confidence=round(best_score, 4), per_level=guesses)

    def classify_record(self, text: str, declared: str | None = None,
                        noun_phrase: str | None = None) -> Classification:
        """A family's declared class wins outright. Nothing is inferred that is known.

        Where it must be inferred, the EXTRACTED noun phrase is classified rather than the
        raw description. Raw text fails twice over: "BLT HEX HD" contains no word the
        taxonomy knows, and in "PLAIN WASHER M16 STAINLESS" the material word outranks the
        item noun and lands the record under steel alloys instead of washers. Extraction has
        already worked out what the thing is; classification should use that answer rather
        than re-deriving it from the same messy string.
        """
        if declared and declared in self.tax.by_code:
            node = self.tax.by_code[declared]
            return Classification(
                code=declared, level=node.level, path=self.tax.label(declared),
                decided_by="declared", confidence=1.0)
        if noun_phrase:
            guess = self.classify(noun_phrase, scope=self.MRO_SEGMENTS)
            if guess.code:
                guess.decided_by = "noun phrase"
                return guess
        return self.classify(text)
