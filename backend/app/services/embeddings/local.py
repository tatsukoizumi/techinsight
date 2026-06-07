"""Local embedder backed by sentence-transformers (offline, no API key)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.embeddings.base import BaseEmbedder

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class LocalEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, dim: int) -> None:
        # Imported lazily so the heavy torch/transformers stack is only loaded
        # when the local provider is actually used.
        from sentence_transformers import SentenceTransformer

        self._model: SentenceTransformer = SentenceTransformer(model_name)
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()
