"""OpenAI embedder (opt-in via OPENAI_API_KEY)."""

from __future__ import annotations

from app.services.embeddings.base import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, dim: int, api_key: str) -> None:
        # Lazy import keeps the openai client optional at runtime.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model_name
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
