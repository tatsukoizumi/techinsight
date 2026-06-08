# TechInsight

技術記事を対象とした **AI 搭載ナレッジベース**。記事の CRUD に加え、**キーワード検索**と
**セマンティック（ベクトル）検索**を提供する。

> 評価者のローカルマシンで **`docker compose up` だけ**で、API キー不要・完全オフラインで
> 全機能が動くことを最優先要件として設計している。

## クイックスタート

前提は **Docker** と **Docker Compose v2** のみ（言語ランタイムのローカル導入は不要）。

```bash
git clone <this-repo>
cd techinsight
docker compose up --build
```

初回起動で `db`（PostgreSQL16 + pgvector）→ `migrator`（Alembic スキーマ作成 →
`data/articles.csv` 1,000 件を埋め込み付きで取り込み）→ `backend` → `frontend` が順に立ち上がる。

| 画面 / API       | URL                                                          |
| ---------------- | ------------------------------------------------------------ |
| フロントエンド   | [http://localhost:3000](http://localhost:3000)               |
| API ドキュメント | [http://localhost:8000/docs](http://localhost:8000/docs)     |
| ヘルスチェック   | [http://localhost:8000/health](http://localhost:8000/health) |

```bash
docker compose down      # 停止（DB データは保持）
docker compose down -v   # 停止 + DB データ削除（クリーンな再取り込み）
```

> 埋め込みモデル（`all-MiniLM-L6-v2`）は backend イメージに焼き込み済みで、起動時の
> ダウンロードは発生しない（`HF_HUB_OFFLINE=1`）。

## 主な機能

- **記事 CRUD** — 一覧（ページネーション・カテゴリ絞り込み・新着/古い順）、詳細、作成、編集、削除。
- **2 種類の検索**（タブで切替）
  - **言葉で探す（キーワード）** — PostgreSQL 全文検索（`tsvector` + GIN）。固有名詞・完全一致に強い。
  - **意味で探す（セマンティック）** — pgvector + HNSW のコサイン類似度。言い換え・自然文に強い。

## 技術スタック

| 層         | 採用                                                                             |
| ---------- | -------------------------------------------------------------------------------- |
| Backend    | Python 3.14 / FastAPI / SQLAlchemy 2.x (async) / Alembic / Pydantic v2 / asyncpg |
| 検索 DB    | PostgreSQL 16 + pgvector（`tsvector`/GIN ＋ `vector`/HNSW）                      |
| 埋め込み   | sentence-transformers `all-MiniLM-L6-v2`（384 次元・ローカル）/ OpenAI 切替可    |
| Frontend   | Next.js 16 / React 19 / TypeScript / Tailwind CSS v4 / TanStack Query            |
| UI         | shadcn/ui（Radix ベース・自前ソース）。状態は TanStack Query + React 標準        |
| Infra      | Docker Compose（`db` / `migrator` / `backend` / `frontend`）                     |
| 品質ツール | Backend: Ruff / Frontend: Biome + Knip / Docs: Prettier                          |

## 工夫した点

- **薄い構成を貫く** — 「便利そう」での依存追加をしない。状態管理ライブラリを入れず（TanStack Query
  ＋ React 標準）、UI は shadcn/ui 方式で必要分だけを自前ソースとして持つ。未使用 export / file / dep は
  **Knip** で検出して消す。AI エージェント設定（`.claude/`）も品質を仕組みで担保する最小限に留める。
- **シンプルな UI と無駄のない UX** — 検索は **Enter キーで実行**（入力中は「Enter で検索」を表示し、
  打鍵ごとの API 呼び出しを抑制）。検索条件（クエリ・モード）を **URL クエリに同期**し、リロード・共有・
  戻る/進むで復元。関連度は 5 段階の色付きバーで可視化。詳細・編集・削除を 1 つのモーダルに集約し、
  作成/編集/削除はキャッシュへ即時反映。
- **スケールを意識した検索 DB 設計** — 用途別インデックス（GIN / HNSW / B-tree）で 10K 件規模でも
  全検索をインデックス経由に。N+1 を避け、取り込みは `content_hash` 差分のみ再 embed。
- **再現性のためのバージョン管理** — ホストのランタイム/ツールは **mise** を SSOT とし、CI も同じ
  `mise.toml` を読む。コンテナは公式 image を使い Dockerfile と手動同期して、ローカル・CI・コンテナの
  バージョンを一致させる。
- **品質を仕組みで担保** — Lint/Format/Dead-code/テストを **CI** で必須化、**Dependabot** で依存を
  週次グルーピング更新、`/audit`（pnpm audit + pip-audit）で脆弱性を監査。`main` は保護ブランチとし
  PR + CI グリーンを必須とする。

詳細は [開発・運用ガイド](docs/development.md)、設計判断は
[実装プラン](docs/IMPLEMENTATION_PLAN.md)、仕様は
[DB 設計書](docs/db-design.md) / [API 設計書](docs/api-design.md) を参照。

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
                                   （tsvector/GIN ＋ vector/HNSW）
```

`backend` は薄いルーター（`api/`）＋ ビジネスロジック（`services/`：検索・埋め込み）＋
クエリ（`repositories/`）にレイヤ分離し、テスト容易性を確保。重い取り込み処理は
`migrator` サービスに分離し、backend の起動・再起動を軽く保つ。

## 環境変数

`.env` は任意。未作成でも `docker-compose.yml` の既定値で起動する（`cp .env.example .env` で編集可、
`.env` は Git 管理外）。主なもの:

| 変数                 | 既定値  | 説明                      |
| -------------------- | ------- | ------------------------- |
| `EMBEDDING_PROVIDER` | `local` | `local`（既定）/ `openai` |
| `OPENAI_API_KEY`     | （空）  | `openai` 選択時のみ必要   |
| `BACKEND_PORT`       | `8000`  | backend 公開ポート        |
| `FRONTEND_PORT`      | `3000`  | frontend 公開ポート       |

> **OpenAI 埋め込みへの切替（任意・評価には不要）:** `.env` で `EMBEDDING_PROVIDER=openai` ＋
> `OPENAI_API_KEY=sk-...` を設定。HNSW は固定次元（local=384 / OpenAI=1536）のため、次元が変わる
> 切替には `docker compose down -v` でボリュームを作り直す。

## ローカル開発・テスト

ホストのランタイムは [mise](https://mise.jdx.dev/) で固定。手順・品質チェック・CI の詳細は
[開発・運用ガイド](docs/development.md) を参照。

```bash
mise install && pnpm install   # ランタイム取得 + 依存
cd backend && uv run pytest    # backend テスト（testcontainers で本物の pgvector を起動）
pnpm quality                   # frontend/docs の Lint + Format + Dead-code
```

## トラブルシュート

| 症状                             | 対処                                                                        |
| -------------------------------- | --------------------------------------------------------------------------- |
| ポート競合（3000 / 8000 / 5432） | `.env` で `FRONTEND_PORT` / `BACKEND_PORT` / `POSTGRES_PORT` を変更         |
| 初回 backend ビルドが遅い        | torch ＋ モデル焼き込みで初回のみ時間がかかる。2 回目以降はキャッシュで高速 |
| 検索結果が 0 件                  | `migrator` の取り込み完了を待つ（`docker compose logs migrator`）           |
| provider 切替後に次元不一致      | `docker compose down -v` してから再起動（上記「OpenAI 切替」参照）          |
| データを初期状態に戻したい       | `docker compose down -v && docker compose up`                               |
