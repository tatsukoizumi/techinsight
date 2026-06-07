"""Test fixtures: a real pgvector PostgreSQL via testcontainers.

sqlite has no tsvector/pgvector, so tests run against the same engine as
production. The schema is created by the actual Alembic migration so tests
exercise the real DDL (generated column, HNSW index, trigger).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import ClassVar

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command

# A deterministic embedding dimension matching Settings (local provider = 384).
EMBED_DIM = 384


@pytest.fixture(scope="session")
def db_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url

        from app.core.config import get_settings

        get_settings.cache_clear()

        # Run the real migration against the container.
        command.upgrade(Config("alembic.ini"), "head")
        yield url


@pytest_asyncio.fixture
async def session(db_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(db_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE articles RESTART IDENTITY CASCADE"))
        await s.commit()
        yield s
    await engine.dispose()


class FakeEmbedder:
    """Deterministic bag-of-keywords embedder for ranking assertions.

    Each known keyword maps to a one-hot axis; a text's vector is the sum of its
    keyword axes, L2-normalized and padded to EMBED_DIM. Texts sharing keywords
    therefore have high cosine similarity, which makes semantic ranking testable.
    """

    KEYWORDS: ClassVar[list[str]] = [
        "postgres",
        "kubernetes",
        "docker",
        "python",
        "react",
        "vector",
    ]

    @property
    def dim(self) -> int:
        return EMBED_DIM

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def encode_one(self, text: str) -> list[float]:
        return self._vec(text)

    def _vec(self, text: str) -> list[float]:
        lowered = text.lower()
        raw = [1.0 if kw in lowered else 0.0 for kw in self.KEYWORDS]
        norm = sum(x * x for x in raw) ** 0.5 or 1.0
        head = [x / norm for x in raw]
        return head + [0.0] * (EMBED_DIM - len(head))


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest_asyncio.fixture
async def client(session: AsyncSession, fake_embedder: FakeEmbedder) -> AsyncIterator[AsyncClient]:
    from app.core.db import get_session
    from app.core.deps import embedder_dependency
    from app.main import app

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[embedder_dependency] = lambda: fake_embedder
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
