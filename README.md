# TechInsight

技術記事を対象とした **AI 搭載ナレッジベース**。記事の CRUD に加え、**キーワード検索**・
**セマンティック（ベクトル）検索**を提供する。

評価者のローカルマシンで **`docker compose up` 1 コマンド**だけで、API キー不要・完全
オフラインで全機能が再現できることを最優先要件として設計している。

---

## クイックスタート

前提: **Docker** と **Docker Compose v2** のみ（言語ランタイムのローカル導入は不要）。

```bash
git clone <this-repo>
cd techinsight
docker compose up --build
```

初回起動時に以下が自動実行される:

1. `db` … PostgreSQL 16 + pgvector を起動
2. `migrator` … Alembic でスキーマ作成 → `data/articles.csv`（1,000 件）を取り込み（埋め込み生成込み）
3. `backend` … FastAPI 起動
4. `frontend` … Next.js 開発サーバ起動

起動後のアクセス先:

| 画面 / API       | URL                          |
| ---------------- | ---------------------------- |
| フロントエンド   | http://localhost:3000        |
| バックエンド API | http://localhost:8000        |
| API ドキュメント | http://localhost:8000/docs   |
| ヘルスチェック   | http://localhost:8000/health |

> 埋め込みモデル（`all-MiniLM-L6-v2`）は backend イメージにビルド時へ焼き込んでおり、
> 起動時のダウンロードは発生しない（`HF_HUB_OFFLINE=1`）。

### 停止・リセット

```bash
docker compose down       # 停止（DB データは保持）
docker compose down -v    # 停止 + DB データ削除（クリーンな再取り込み）
```

---

## 主な機能

- **記事 CRUD**: 一覧（ページネーション・カテゴリ絞り込み・新着/古い順）、詳細表示、作成、編集、削除。
- **2 種類の検索**（タブで切替）:
  - **言葉で探す（キーワード）**: PostgreSQL 全文検索（`tsvector` + GIN）。固有名詞・完全一致に強い。
  - **意味で探す（セマンティック）**: 文の意味で検索（pgvector + HNSW、コサイン類似度）。言い換えに強い。
- **UX**: 検索は **Enter キーで実行**（入力中は「Enter で検索」を表示。無駄な API 呼び出しを抑制）、
  検索結果は関連度を 5 段階の色付きバーで表示、削除前の確認、作成・編集・削除後のキャッシュ即時反映。

---

## 技術スタック

| 層         | 採用                                                                             |
| ---------- | -------------------------------------------------------------------------------- |
| Backend    | Python 3.14 / FastAPI / SQLAlchemy 2.x (async) / Alembic / Pydantic v2 / asyncpg |
| 検索 DB    | PostgreSQL 16 + pgvector（`tsvector`/GIN + `vector`/HNSW）                       |
| 埋め込み   | sentence-transformers `all-MiniLM-L6-v2`（384 次元・ローカル）/ OpenAI 切替可    |
| Frontend   | Next.js 16 / React 19 / TypeScript / Tailwind CSS v4 / TanStack Query            |
| UI         | shadcn/ui（Radix ベース）。状態管理は React 標準（TanStack Query + useState）    |
| Infra      | Docker Compose（`db` / `migrator` / `backend` / `frontend`）                     |
| 品質ツール | Backend: Ruff / Frontend: Biome + Knip / Docs: Prettier                          |

設計判断・フェーズの詳細は [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)、
DB / API 仕様は [`docs/db-design.md`](docs/db-design.md) /
[`docs/api-design.md`](docs/api-design.md) を参照。

---

## 環境変数

`.env` は任意。未作成でも `docker-compose.yml` の既定値で起動する。必要なら
`cp .env.example .env` して編集する（`.env` は Git 管理外）。

| 変数                        | 既定値                  | 説明                            |
| --------------------------- | ----------------------- | ------------------------------- |
| `POSTGRES_USER/PASSWORD/DB` | `techinsight` 系        | DB 認証情報                     |
| `BACKEND_PORT`              | `8000`                  | backend 公開ポート              |
| `FRONTEND_PORT`             | `3000`                  | frontend 公開ポート             |
| `DATABASE_URL`              | asyncpg URL             | backend → DB 接続               |
| `NEXT_PUBLIC_API_BASE`      | `http://localhost:8000` | ブラウザ → backend のベース URL |
| `EMBEDDING_PROVIDER`        | `local`                 | `local`（既定）/ `openai`       |
| `OPENAI_API_KEY`            | （空）                  | `openai` 選択時のみ必要         |

---

## OpenAI 埋め込みへの切り替え（任意）

評価には不要（既定の local で完全動作）。試す場合のみ:

```bash
# .env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

HNSW インデックスは固定次元（local=384 / OpenAI=1536）のため、**次元が変わる切り替えには
ボリュームの作り直しが必要**:

```bash
docker compose down -v          # 384 次元のデータ・インデックスを破棄
docker compose up --build       # 1536 次元で再マイグレーション + 再取り込み
```

---

## ローカル開発

ホスト側のランタイムは [mise](https://mise.jdx.dev/) で固定（`mise.toml`）。

```bash
mise install            # Node 24 / Python 3.14 / uv を取得
corepack enable         # pnpm 11.5.2 を有効化
pnpm install            # workspace 全体（root + frontend）

# バックエンドのみ（DB はコンテナ、API はホットリロード）
docker compose up -d db
cd backend && uv sync && uv run uvicorn app.main:app --reload

# フロントエンドのみ
pnpm fe:dev
```

CSV を再取り込みしたいとき（idempotent: 既存は UPSERT、変更分のみ再 embed）:

```bash
docker compose run --rm migrator
```

---

## テスト・品質チェック

```bash
# Backend: pytest（testcontainers が本物の pgvector PostgreSQL を起動）
cd backend && uv run pytest

# Backend: Lint / Format
cd backend && uv run ruff check . && uv run ruff format --check .

# Frontend / Docs: Biome + Knip + Prettier
pnpm quality
```

> テストは sqlite を使わず、本番と同じ pgvector PostgreSQL に対して実行する
> （`tsvector` / `vector` は sqlite 非対応のため）。キーワード/セマンティック検索の順位を検証する。

---

## トラブルシュート

| 症状                              | 対処                                                                             |
| --------------------------------- | -------------------------------------------------------------------------------- |
| ポート競合（3000 / 8000 / 5432）  | `.env` で `FRONTEND_PORT` / `BACKEND_PORT` / `POSTGRES_PORT` を変更              |
| 初回 backend ビルドが遅い         | torch + モデル焼き込みで初回のみ時間がかかる。2 回目以降はレイヤキャッシュで高速 |
| 検索結果が 0 件                   | `migrator` の取り込み完了を待つ（`docker compose logs migrator`）                |
| provider 切替後に次元不一致エラー | `docker compose down -v` してから再起動（上記「OpenAI 切り替え」参照）           |
| データを初期状態に戻したい        | `docker compose down -v && docker compose up`                                    |

---

## アーキテクチャ

```
ブラウザ ──→ frontend (Next.js)
                │  fetch (NEXT_PUBLIC_API_BASE)
                ▼
            backend (FastAPI)
        api/ ─ services/ ─ repositories/ ─ models/
                │                              │
        embeddings(local/openai)         SQLAlchemy(async)
                                               ▼
                                   PostgreSQL 16 + pgvector
                                   （tsvector/GIN + vector/HNSW）
```

- **backend** は薄いルーター（`api/`）＋ ビジネスロジック（`services/`：検索・埋め込み）
  ＋ クエリ（`repositories/`）でレイヤ分離し、テスト容易性を確保。
- **migrator** を独立させ、重い取り込み処理を backend の起動・再起動から切り離している。

---

## 設計上の工夫

- **UI/UX**: 検索モードをタブで即切替、Enter 実行で無駄な API 呼び出しを抑制、関連度を 5 段階で
  可視化、楽観的なキャッシュ更新で作成・編集・削除が一覧/検索へ即反映。詳細・編集・削除を 1 つのモーダルに集約。
- **DB / スケーラビリティ**: 用途別インデックス（GIN / HNSW / B-tree）で 10K 件規模でも
  全検索をインデックス経由に。N+1 を避け、取り込みは `content_hash` 差分のみ再計算。
- **チーム開発意識**: Conventional Commits、Lint/Format/Dead-code をツールで強制、
  DB スキーマは Alembic 一元管理、設定は型付き Settings に集約（`embedding_dim` は SSOT）。
- **保守運用**: 環境変数で provider を差し替え可能な抽象、`migrator` 分離による軽い再起動、
  バージョンは `mise.toml` と Dockerfile を同期させて再現性を担保。
