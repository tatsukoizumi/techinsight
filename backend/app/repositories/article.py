"""SQLAlchemy data access for articles (queries only, no business logic)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article

Sort = Literal["newest", "oldest"]


def _to_vector_literal(vector: list[float]) -> str:
    """Render a Python vector as a pgvector text literal: [a,b,c]."""
    return "[" + ",".join(repr(x) for x in vector) + "]"


async def get(session: AsyncSession, article_id: int) -> Article | None:
    return await session.get(Article, article_id)


async def list_articles(
    session: AsyncSession,
    *,
    page: int,
    size: int,
    category: str | None = None,
    author: str | None = None,
    sort: Sort = "newest",
) -> tuple[list[Article], int]:
    filters = []
    if category:
        filters.append(Article.category == category)
    if author:
        filters.append(Article.author == author)

    total = await session.scalar(select(func.count()).select_from(Article).where(*filters))

    order = Article.published_at.asc() if sort == "oldest" else Article.published_at.desc()
    stmt = (
        select(Article)
        .where(*filters)
        .order_by(order, Article.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = list((await session.scalars(stmt)).all())
    return rows, int(total or 0)


async def create(session: AsyncSession, values: dict[str, Any]) -> Article:
    article = Article(**values)
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return article


async def update(session: AsyncSession, article: Article, values: dict[str, Any]) -> Article:
    for key, value in values.items():
        setattr(article, key, value)
    await session.commit()
    await session.refresh(article)
    return article


async def delete(session: AsyncSession, article: Article) -> None:
    await session.delete(article)
    await session.commit()


async def search_keyword(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
    category: str | None = None,
) -> list[tuple[int, float]]:
    """Return (id, ts_rank) ordered best-first via the GIN tsvector index."""
    cat_clause = "AND category = :category" if category else ""
    sql = text(f"""
        SELECT id, ts_rank(search_tsv, plainto_tsquery('english', :q)) AS score
        FROM articles
        WHERE search_tsv @@ plainto_tsquery('english', :q)
        {cat_clause}
        ORDER BY score DESC, published_at DESC
        LIMIT :k
    """)
    params: dict[str, Any] = {"q": query, "k": limit}
    if category:
        params["category"] = category
    result = await session.execute(sql, params)
    return [(row.id, float(row.score)) for row in result]


async def search_semantic(
    session: AsyncSession,
    *,
    query_vector: list[float],
    limit: int,
    category: str | None = None,
) -> list[tuple[int, float]]:
    """Return (id, cosine_similarity) ordered best-first via the HNSW index."""
    cat_clause = "AND category = :category" if category else ""
    sql = text(f"""
        SELECT id, 1 - (embedding <=> (:vec)::vector) AS score
        FROM articles
        WHERE embedding IS NOT NULL
        {cat_clause}
        ORDER BY embedding <=> (:vec)::vector
        LIMIT :k
    """)
    params: dict[str, Any] = {"vec": _to_vector_literal(query_vector), "k": limit}
    if category:
        params["category"] = category
    result = await session.execute(sql, params)
    return [(row.id, float(row.score)) for row in result]


async def get_many(session: AsyncSession, ids: list[int]) -> dict[int, Article]:
    if not ids:
        return {}
    rows = (await session.scalars(select(Article).where(Article.id.in_(ids)))).all()
    return {row.id: row for row in rows}
