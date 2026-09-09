"""Embedding backends.

Retrieval runs locally by default. That is a deliberate architectural choice, not a cost
saving: candidate search never sends a material description off the machine, so only the
genuinely ambiguous pairs ever reach a hosted model. It is what makes the on-premises
claim true rather than aspirational.

Embeddings are used ONLY to propose candidates. They never decide a match. A general
sentence model scores "M16X80" and "M16X50" as nearly identical, which is acceptable for
proposing and would be dangerous for deciding.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

DEFAULT_LOCAL_MODEL = "BAAI/bge-base-en-v1.5"


class Embedder(Protocol):
    dimension: int
    name: str

    def encode(self, texts: list[str]) -> np.ndarray: ...


class LocalEmbedder:
    """Sentence-transformer running in-process. No network call after the first download."""

    def __init__(self, model_name: str = DEFAULT_LOCAL_MODEL, device: str | None = None,
                 batch_size: int = 64) -> None:
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self._batch = batch_size
        self._model = SentenceTransformer(model_name, device=device)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        # Vectors come back L2-normalised, so cosine similarity is a plain dot product.
        # No query instruction prefix: this model family recommends one only for short
        # query against long passage. Ours is description against description, which is
        # symmetric, and a prefix would hurt.
        return self._model.encode(
            texts,
            batch_size=self._batch,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
