"""Select the embedder based on Settings.embedding_provider."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.embeddings.base import BaseEmbedder


@lru_cache
def get_embedder() -> BaseEmbedder:
    """Build the configured embedder once and cache it (model load is expensive)."""
    settings = get_settings()

    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY to be set")
        from app.services.embeddings.openai import OpenAIEmbedder

        return OpenAIEmbedder(
            model_name=settings.openai_embedding_model,
            dim=settings.embedding_dim,
            api_key=settings.openai_api_key,
        )

    from app.services.embeddings.local import LocalEmbedder

    return LocalEmbedder(model_name=settings.local_embedding_model, dim=settings.embedding_dim)
