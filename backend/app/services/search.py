"""Search orchestration: keyword and semantic retrieval."""

from __future__ import annotations

from typing import Literal

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.repositories import article as repo
from app.services.embeddings.base import BaseEmbedder

SearchMode = Literal["keyword", "semantic"]


async def _attach(
    session: AsyncSession, ranked: list[tuple[int, float]]
) -> list[tuple[Article, float]]:
    """Resolve (id, score) pairs to (Article, score), preserving rank order."""
    by_id = await repo.get_many(session, [doc_id for doc_id, _ in ranked])
    return [(by_id[doc_id], score) for doc_id, score in ranked if doc_id in by_id]


async def search(
    session: AsyncSession,
    embedder: BaseEmbedder,
    *,
    query: str,
    mode: SearchMode,
    limit: int,
    category: str | None = None,
) -> list[tuple[Article, float]]:
    if mode == "semantic":
        # Embedding is CPU-bound; keep the event loop responsive.
        vector = await run_in_threadpool(embedder.encode_one, query)
        ranked = await repo.search_semantic(
            session, query_vector=vector, limit=limit, category=category
        )
    else:
        ranked = await repo.search_keyword(session, query=query, limit=limit, category=category)
    return await _attach(session, ranked)
