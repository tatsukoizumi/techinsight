# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

TechInsight は技術記事を対象とした AI 搭載ナレッジベース。CRUD + キーワード検索 + セマンティック（ベクトル）検索を提供する。
コーディング試験課題のため、評価者のローカルマシンで `docker compose up` 1 コマンドで完全再現できることが必須要件。

詳細な要件・実装フェーズ・成果物リストは `docs/IMPLEMENTATION_PLAN.md` を参照。元の試験要件は `docs/requirements.md` に保管。

## 技術スタック

- **Backend:** Python 3.11 / FastAPI / SQLAlchemy 2.x (async) / Alembic / Pydantic v2
- **Frontend:** Next.js 14 (App Router) / TypeScript / React / Tailwind CSS / TanStack Query
- **DB:** PostgreSQL 16 + `pgvector` 拡張
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`（384 次元、ローカル動作・APIキー不要がデフォルト）。`OPENAI_API_KEY` が環境変数にあれば OpenAI `text-embedding-3-small` に切り替える provider 抽象を持つ。
- **Infra:** Docker Compose（`db` / `backend` / `frontend` / 一回限りの `migrator` サービス）

## 主要コマンド

```bash
# 全サービス起動（DBマイグレーション + CSV取り込み + API + フロント）
docker compose up --build

# バックエンドのみ（ローカル開発、ホットリロード）
docker compose up db
cd backend && uv sync && uv run uvicorn app.main:app --reload

# フロントエンドのみ
cd frontend && pnpm install && pnpm dev

# テスト
cd backend && uv run pytest                    # 全テスト
cd backend && uv run pytest tests/test_search.py::test_semantic_ranking -v  # 単体
cd frontend && pnpm test                       # Vitest
cd frontend && pnpm test:e2e                   # Playwright（任意）

# Lint / Format
cd backend && uv run ruff check . && uv run ruff format .
cd frontend && pnpm lint && pnpm typecheck

# マイグレーション
cd backend && uv run alembic revision --autogenerate -m "message"
cd backend && uv run alembic upgrade head

# CSV 再取り込み（idempotent: 既存IDは UPSERT、embedding を再計算）
docker compose run --rm backend python -m app.scripts.ingest_articles data/articles.csv
```

## アーキテクチャ要点

### 検索の二層構造（最重要）
セマンティック検索だけだと完全一致や固有名詞に弱いため、**ハイブリッド検索**を実装する：
1. **キーワード検索:** PostgreSQL の `tsvector` + GIN インデックス（`title`, `content` を generated column で `tsvector` 化）
2. **セマンティック検索:** `content` の embedding を pgvector の `vector(384)` カラムに保存、`HNSW` インデックスでコサイン類似度検索
3. **融合:** Reciprocal Rank Fusion (RRF) で両者をマージ。`GET /api/search?q=...&mode=hybrid|keyword|semantic` で切替可能にする。

10K 件想定のスケール要件のため、**インデックス設計が肝**：
- `embedding` カラム: `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
- `search_tsv` generated column + GIN
- `category`, `published_at` に B-tree（フィルタ + ソート用）

### Embedding プロバイダ抽象
`backend/app/services/embeddings/` 配下に `BaseEmbedder` インターフェースを置き、`LocalEmbedder`（sentence-transformers）と `OpenAIEmbedder` を実装。`Settings.embedding_provider` で切替。**評価者は API キーを持たない前提なので、デフォルトは local。**OpenAI 側は 1536 次元になるため、provider 切替時は再 ingest が必要 — README にその旨を明記する。

### CSV 取り込みパイプライン
`docker compose up` の初回起動時、`migrator` サービスが `alembic upgrade head` → `python -m app.scripts.ingest_articles` を実行。再実行時は ID で UPSERT し、`content_hash` が変わったレコードのみ embedding を再計算する（10K スケールで全件再計算を避ける）。

### Backend レイヤリング
- `app/api/` — FastAPI ルーター（薄く、Pydantic スキーマで I/O のみ）
- `app/services/` — ビジネスロジック（検索融合、embedding 生成）
- `app/repositories/` — SQLAlchemy クエリ（テスト容易化のため抽象）
- `app/models/` — SQLAlchemy ORM
- `app/schemas/` — Pydantic
- `app/core/` — 設定、DB セッション、依存性注入

非同期 SQLAlchemy + `asyncpg` ドライバ。embedding 計算は CPU バウンドなので `run_in_threadpool` で逃がす。

### Frontend 構造
- `app/` — Next.js App Router（記事一覧、検索、詳細はモーダル）
- `components/` — 再利用 UI（`ArticleCard`, `ArticleModal`, `SearchBar`）
- `lib/api/` — 型付き API クライアント（OpenAPI から生成、または手書きで十分）
- `lib/hooks/` — TanStack Query フック（`useArticles`, `useSearch`, `useCreateArticle` …）

SSR ではなくクライアント側でフェッチ（管理機能が中心のため）。

## 重要な制約・規約

- **評価者環境を絶対に壊さない:** README の手順通りに `docker compose up` だけで動くこと。任意の API キーは `.env.example` でオプトイン形式にする。
- **シークレットを Git に含めない:** `.env` は `.gitignore`。`.env.example` のみコミット。
- **マイグレーションは Alembic 一本化:** 手動 SQL を使わない。pgvector 拡張の有効化も Alembic の最初のマイグレーションで `CREATE EXTENSION IF NOT EXISTS vector` を実行。
- **10K スケールを意識:** N+1 を作らない（必要なら `selectinload`）、ページネーションは keyset 推奨だが limit/offset でも可、検索は必ずインデックス経由。
- **言語:** ユーザ向けドキュメント（README, docs/）は日本語、コード内コメントは最小限・英語可。コミットメッセージは日本語可。
