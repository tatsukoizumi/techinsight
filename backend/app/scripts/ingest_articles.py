"""Idempotent CSV ingestion.

Usage:
    python -m app.scripts.ingest_articles /data/articles.csv

Processes the CSV in chunks (never loads the whole file into memory). For each
chunk it looks up existing (id, content_hash) rows in one query and only
re-embeds + upserts rows that are new or whose content changed, so re-running is
cheap at 10K scale. Finally it advances the id sequence past the imported max id
so future inserts don't collide with CSV ids.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.db import SessionLocal, engine
from app.models.article import Article
from app.services.embeddings import get_embedder

CHUNK_SIZE = 256


def _content_hash(title: str, content: str) -> str:
    return hashlib.sha256((title + content).encode("utf-8")).hexdigest()


def _parse_published_at(value: str) -> datetime:
    # CSV uses "2025-09-19 22:00:00" (naive). Treat as UTC for a timestamptz column.
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _read_chunks(csv_path: Path, size: int) -> Iterator[list[dict[str, str]]]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        chunk: list[dict[str, str]] = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


async def ingest(csv_path: Path) -> None:
    embedder = get_embedder()
    total = inserted_or_updated = skipped = 0

    async with SessionLocal() as session:
        for chunk in _read_chunks(csv_path, CHUNK_SIZE):
            total += len(chunk)
            ids = [int(r["id"]) for r in chunk]

            result = await session.execute(
                select(Article.id, Article.content_hash).where(Article.id.in_(ids))
            )
            existing = {row.id: row.content_hash for row in result}

            # Rows that are new or whose content changed need (re-)embedding.
            pending: list[dict[str, object]] = []
            for r in chunk:
                rid = int(r["id"])
                chash = _content_hash(r["title"], r["content"])
                if existing.get(rid) == chash:
                    skipped += 1
                    continue
                pending.append(
                    {
                        "id": rid,
                        "title": r["title"],
                        "content": r["content"],
                        "author": r["author"],
                        "category": r["category"],
                        "published_at": _parse_published_at(r["published_at"]),
                        "content_hash": chash,
                    }
                )

            if not pending:
                continue

            vectors = embedder.encode([str(p["content"]) for p in pending])
            for record, vector in zip(pending, vectors, strict=True):
                record["embedding"] = vector

            stmt = pg_insert(Article).values(pending)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Article.id],
                set_={
                    "title": stmt.excluded.title,
                    "content": stmt.excluded.content,
                    "author": stmt.excluded.author,
                    "category": stmt.excluded.category,
                    "published_at": stmt.excluded.published_at,
                    "content_hash": stmt.excluded.content_hash,
                    "embedding": stmt.excluded.embedding,
                },
            )
            await session.execute(stmt)
            await session.commit()
            inserted_or_updated += len(pending)
            print(f"  processed {total} rows ({inserted_or_updated} upserted)", file=sys.stderr)

        # Advance the sequence past CSV ids so new inserts don't collide.
        max_id = (
            await session.execute(select(func.coalesce(func.max(Article.id), 1)))
        ).scalar_one()
        await session.execute(text("SELECT setval('articles_id_seq', :v)").bindparams(v=max_id))
        await session.commit()

    await engine.dispose()
    print(
        f"Ingest complete: {total} rows, {inserted_or_updated} upserted, {skipped} unchanged",
        file=sys.stderr,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m app.scripts.ingest_articles <csv_path>", file=sys.stderr)
        raise SystemExit(2)
    csv_path = Path(sys.argv[1])
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        raise SystemExit(1)
    asyncio.run(ingest(csv_path))


if __name__ == "__main__":
    main()
