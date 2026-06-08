# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

TechInsight は技術記事を対象とした AI 搭載ナレッジベース。CRUD + キーワード検索 + セマンティック（ベクトル）検索を提供する。
コーディング試験課題のため、評価者のローカルマシンで `docker compose up` 1 コマンドで完全再現できることが必須要件。

詳細な要件・実装フェーズ・成果物リストは `docs/IMPLEMENTATION_PLAN.md` を参照。元の試験要件は `docs/requirements.md` に保管。

## 技術スタック

- **Backend:** Python **3.14**（最新安定版）/ FastAPI / SQLAlchemy 2.x (async) / Alembic / Pydantic v2
- **Frontend:** Next.js（最新）/ TypeScript（最新）/ React / Tailwind CSS / TanStack Query
- **Node:** **24 LTS**（latest LTS）— `mise.toml` で固定
- **pnpm:** **11.5.2** — `mise.toml` で管理（`packageManager` フィールドにも明記して同期）。
- **DB:** PostgreSQL 16 + `pgvector` 拡張
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`（384 次元、ローカル動作・APIキー不要がデフォルト）。`OPENAI_API_KEY` が環境変数にあれば OpenAI `text-embedding-3-small` に切り替える provider 抽象を持つ。
- **Infra:** Docker Compose（`db` / `backend` / `frontend` / 一回限りの `migrator` サービス）。コンテナは公式 image（`python:3.14.5-slim` + Astral 公式 uv バイナリ COPY、`node:24.16.0-bookworm-slim` + `npm i -g pnpm@11.5.2`）を使用。ホスト側の `mise.toml` と同じバージョンを Dockerfile FROM 行に書いて同期。
- **Monorepo / 品質ツール:** pnpm workspaces。**Prettier**（root: Markdown / YAML / root JSON）+ **Biome**（frontend: Lint + Format + Import 並び替え）+ **Knip**（frontend: 未使用 export / file / dep 検出）。Backend 側は **Ruff**（Lint + Format）。役割が重複しないよう `.prettierignore` で `frontend/` を除外している。

## 主要コマンド

```bash
# 初回セットアップ（mise でランタイム + pnpm 取得 → 依存）
mise install                                   # Node 24 + Python 3.14 + uv + pnpm 11.5.2（mise.toml に従う）
pnpm install                                   # workspace 全体（root + frontend）

# 環境変数（任意。docker-compose.yml にデフォルトが入っているので未作成でも起動はする）
cp .env.example .env

# 全サービス起動（DB + migrator + backend + frontend）
docker compose up --build
docker compose up -d db backend                # ヘッドレスで DB と backend のみ
docker compose down                            # 停止（DB データは保持）
docker compose down -v                         # DB データも削除
docker compose logs -f backend                 # 個別ログ
curl -s http://localhost:8000/health           # backend ヘルスチェック

# バックエンドのみ（ローカル開発、ホットリロード）
docker compose up db
cd backend && uv sync && uv run uvicorn app.main:app --reload

# フロントエンドのみ
pnpm fe:dev                                    # = pnpm --filter frontend dev

# テスト
cd backend && uv run pytest                    # 全テスト
cd backend && uv run pytest tests/test_search.py::test_semantic_ranking -v  # 単体
pnpm --filter frontend test                    # Vitest
pnpm --filter frontend test:e2e                # Playwright（任意）

# 品質チェック（lint / format / dead-code）
pnpm quality                                   # Prettier --check + Biome check + Knip 全部
pnpm check                                     # Prettier + Biome のみ（dead-code 除く、速い）
pnpm fix                                       # Prettier --write + Biome --write
pnpm format / pnpm format:check                # Prettier 単体（Markdown / YAML / root JSON）
pnpm fe:check / pnpm fe:check:fix              # Biome 単体（frontend の TS/TSX/JS/JSON）
pnpm fe:knip                                   # 未使用 export / file / dep を検出
cd backend && uv run ruff check . && uv run ruff format .

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
3. **融合:** Reciprocal Rank Fusion (RRF) で両者をマージ。`GET /api/v1/search?q=...&mode=hybrid|keyword|semantic` で切替可能にする（業務 API は `/api/v1` 配下。インフラ用 `/health` のみ非バージョン）。

10K 件想定のスケール要件のため、**インデックス設計が肝**：

- `embedding` カラム: `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
- `search_tsv` generated column + GIN
- `category`, `published_at` に B-tree（フィルタ + ソート用）

### Embedding プロバイダ抽象

`backend/app/services/embeddings/` 配下に `BaseEmbedder` インターフェースを置き、`LocalEmbedder`（sentence-transformers）と `OpenAIEmbedder` を実装。`Settings.embedding_provider` で切替。**評価者は API キーを持たない前提なので、デフォルトは local。**埋め込み次元は `Settings.embedding_dim`（local=384 / OpenAI=1536）を single source of truth とし、`embedding` カラムと HNSW インデックスは Alembic マイグレーションがこの値を読んで生成する。HNSW は固定次元のため、**provider を切り替える際は DB volume を削除 → 再マイグレーション → 再 ingest が必要**（README に明記）。

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

### プロジェクト基本ルール（最優先 — 全コードがこれに従うこと）

1. **フレームワーク・言語は最新バージョンを使う** — Node 24 LTS / Python 3.14 / FastAPI / Next.js / Biome / Prettier すべて執筆時点の最新。新規追加するライブラリも同様。
2. **ホスト側のランタイム / ツールは mise で管理する** — Node / Python / uv のバージョンは `mise.toml` で固定。**コンテナでは公式 image（`python:3.14.5-slim`、`node:24.16.0-bookworm-slim`、`pgvector/pgvector:pg16`）を使用**し、Dockerfile の FROM 行と mise.toml に同じバージョンを書いて手動同期する（コンテナ内に mise レイヤを挟まない方が薄い）。バージョンを上げる際は `mise.toml` と Dockerfile を同じ PR で更新する。
3. **不要なライブラリを入れない** — 「便利そうだから」で追加しない。標準ライブラリや既存ツールで済むなら追加しない。極力薄い構成を維持する。
4. **dead-code は削除する** — 未使用の export / file / dep / import を残さない。機能を消したら関連も同時に消す。
5. **品質ツールを必ず通す** — frontend は `pnpm quality`（Biome + Knip）、backend は `ruff check`、ドキュメントは `prettier --check`。

### その他の規約

- **評価者環境を絶対に壊さない:** README の手順通りに `docker compose up` だけで動くこと。任意の API キーは `.env.example` でオプトイン形式にする。
- **シークレットを Git に含めない:** `.env` は `.gitignore`。`.env.example` のみコミット。
- **マイグレーションは Alembic 一本化:** 手動 SQL を使わない。pgvector 拡張の有効化も Alembic の最初のマイグレーションで `CREATE EXTENSION IF NOT EXISTS vector` を実行。
- **10K スケールを意識:** N+1 を作らない（必要なら `selectinload`）、ページネーションは keyset 推奨だが limit/offset でも可、検索は必ずインデックス経由。
- **言語:** ユーザ向けドキュメント（README, docs/）は日本語、コード内コメントは最小限・英語可。コミットメッセージは日本語可。

## AI エージェント設定基盤（チーム開発）

`.claude/` 配下に、品質ルールを「人間の規律」ではなく「仕組み」で担保する設定を置く。チーム共有分はコミットし、個人設定（`settings.local.json`）は gitignore。

- **hooks（`.claude/settings.json` + `.claude/hooks/format.sh`）:** AI エージェントが Edit/Write した直後に `PostToolUse` hook が**該当ファイルだけ**を拡張子でルーティングして自動整形 + lint する（frontend→Biome / backend→Ruff / docs→Prettier）。自動修正で消えない指摘は exit 2 で差し戻し、エージェントに自己修正させる。Knip は全体解析のため hook には含めず `/check`・CI に委譲。
- **slash commands（`.claude/commands/`）:** `/commit`（規約準拠コミット）、`/check [frontend|backend|all]`（lint+format+dead-code+test を緑まで仕上げる）、`/pr`（Conventional Commits 準拠で PR 作成）。コードレビューは組み込みの `/code-review`・`/review` を使う。
- **skills（`.claude/skills/`）:** プロジェクト固有手順を model 自動発火で提供 — `add-api-endpoint`（レイヤリング + 統合テスト）、`add-migration`（Alembic + embedding 次元 SSOT / HNSW の落とし穴）、`reingest-csv`（idempotent 取り込み）。
- **CI（`.github/workflows/ci.yml`）:** PR / main push で `pnpm quality`・Ruff・pytest を検証する最終防衛線。`jdx/mise-action` で `mise.toml` をバージョンの単一ソースにする。

設定（hooks / permissions / 自動化）を変更したいときは `/update-config` スキルを使う。
