"""Search orchestration: keyword, semantic, and RRF-fused hybrid retrieval."""

from __future__ import annotations

from typing import Literal

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.repositories import article as repo
from app.services.embeddings.base import BaseEmbedder

SearchMode = Literal["hybrid", "keyword", "semantic"]

# Reciprocal Rank Fusion constant. k=60 is the well-known default that dampens
# the influence of very high ranks without ignoring the long tail.
RRF_K = 60


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Fuse several ranked id lists into one.

    Each input list is ordered best-first. An item's fused score is the sum over
    lists of 1 / (k + rank), with rank starting at 1. Pure function so it can be
    unit-tested without a database.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


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
    if mode == "keyword":
        ranked = await repo.search_keyword(session, query=query, limit=limit, category=category)
        return await _attach(session, ranked)

    if mode == "semantic":
        vector = await run_in_threadpool(embedder.encode_one, query)
        ranked = await repo.search_semantic(
            session, query_vector=vector, limit=limit, category=category
        )
        return await _attach(session, ranked)

    # hybrid: retrieve a candidate pool from each side, then fuse with RRF.
    # The two retrievers share one async connection, so they run sequentially
    # (an AsyncSession cannot execute concurrent statements).
    vector = await run_in_threadpool(embedder.encode_one, query)
    keyword_hits = await repo.search_keyword(
        session, query=query, limit=repo.SEARCH_POOL, category=category
    )
    semantic_hits = await repo.search_semantic(
        session, query_vector=vector, limit=repo.SEARCH_POOL, category=category
    )
    fused = reciprocal_rank_fusion(
        [[doc_id for doc_id, _ in keyword_hits], [doc_id for doc_id, _ in semantic_hits]]
    )[:limit]
    return await _attach(session, fused)
