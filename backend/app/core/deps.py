"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.services.embeddings import BaseEmbedder, get_embedder

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def embedder_dependency() -> BaseEmbedder:
    return get_embedder()


EmbedderDep = Annotated[BaseEmbedder, Depends(embedder_dependency)]
