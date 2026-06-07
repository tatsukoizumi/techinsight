"""Application settings (single source of truth for runtime config)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Embedding dimensions per provider. `embedding_dim` is the SSOT consumed by the
# Alembic migration (vector column + HNSW index) and the embedding services.
_PROVIDER_DIMS: dict[str, int] = {"local": 384, "openai": 1536}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # asyncpg-driver URL. Defaults match docker-compose.yml so the app boots
    # without a .env file.
    database_url: str = "postgresql+asyncpg://techinsight:techinsight_dev@db:5432/techinsight"

    embedding_provider: Literal["local", "openai"] = "local"
    openai_api_key: str = ""

    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    @property
    def embedding_dim(self) -> int:
        return _PROVIDER_DIMS[self.embedding_provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
