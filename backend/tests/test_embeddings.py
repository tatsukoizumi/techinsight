"""Unit tests for the embedding provider abstraction (no model download)."""

import pytest

from app.services.embeddings import factory
from app.services.embeddings.base import BaseEmbedder


class FakeEmbedder(BaseEmbedder):
    """Deterministic stand-in used to exercise the interface contract."""

    @property
    def dim(self) -> int:
        return 3

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0, 1.0] for t in texts]


def test_encode_one_delegates_to_encode() -> None:
    assert FakeEmbedder().encode_one("ab") == [2.0, 0.0, 1.0]


def test_encode_empty_returns_empty() -> None:
    assert FakeEmbedder().encode([]) == []


def test_factory_openai_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    factory.get_embedder.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            factory.get_embedder()
    finally:
        get_settings.cache_clear()
        factory.get_embedder.cache_clear()
