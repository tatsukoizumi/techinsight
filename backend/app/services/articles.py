"""Article write orchestration: embedding generation + content hashing + repo."""

from __future__ import annotations

import hashlib

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.repositories import article as repo
from app.schemas.article import ArticleCreate, ArticleUpdate
from app.services.embeddings.base import BaseEmbedder


def content_hash(title: str, content: str) -> str:
    """Stable hash used to detect when an article needs re-embedding."""
    return hashlib.sha256((title + content).encode("utf-8")).hexdigest()


async def create_article(
    session: AsyncSession, embedder: BaseEmbedder, data: ArticleCreate
) -> Article:
    # Embedding is CPU-bound; keep the event loop responsive.
    vector = await run_in_threadpool(embedder.encode_one, data.content)
    values = data.model_dump()
    values["content_hash"] = content_hash(data.title, data.content)
    values["embedding"] = vector
    return await repo.create(session, values)


async def update_article(
    session: AsyncSession,
    embedder: BaseEmbedder,
    article: Article,
    data: ArticleUpdate,
) -> Article:
    values = data.model_dump(exclude_unset=True)
    if not values:
        return article

    new_title = values.get("title", article.title)
    new_content = values.get("content", article.content)

    # Re-embed only when the content actually changed (embeddings are derived
    # from content); refresh the hash whenever title or content changed.
    if "content" in values and values["content"] != article.content:
        values["embedding"] = await run_in_threadpool(embedder.encode_one, new_content)
    if "title" in values or "content" in values:
        values["content_hash"] = content_hash(new_title, new_content)

    return await repo.update(session, article, values)
