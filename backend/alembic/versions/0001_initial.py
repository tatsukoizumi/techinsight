"""initial schema: pgvector extension, articles table, indexes, trigger

Revision ID: 0001
Revises:
Create Date: 2026-06-07

The vector column dimension and HNSW index are generated from
Settings.embedding_dim (SSOT: local=384 / openai=1536).
"""

from collections.abc import Sequence

from alembic import op
from app.core.config import get_settings

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dim = get_settings().embedding_dim

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(f"""
        CREATE TABLE articles (
            id            BIGSERIAL PRIMARY KEY,
            title         TEXT        NOT NULL,
            content       TEXT        NOT NULL,
            author        TEXT        NOT NULL,
            category      TEXT        NOT NULL,
            published_at  TIMESTAMPTZ NOT NULL,
            content_hash  TEXT        NOT NULL,
            embedding     vector({dim}),
            search_tsv    tsvector GENERATED ALWAYS AS (
                            setweight(to_tsvector('english', coalesce(title,'')),   'A') ||
                            setweight(to_tsvector('english', coalesce(content,'')), 'B')
                          ) STORED,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX articles_search_tsv_idx ON articles USING GIN (search_tsv)")
    op.execute(
        "CREATE INDEX articles_embedding_hnsw_idx "
        "ON articles USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("CREATE INDEX articles_category_idx ON articles (category)")
    op.execute("CREATE INDEX articles_published_at_idx ON articles (published_at DESC)")

    # Auto-update updated_at on every row update.
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_set_updated_at
        BEFORE UPDATE ON articles
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS articles")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at")
