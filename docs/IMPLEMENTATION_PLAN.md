# TechInsight 実装計画

最終更新: 2026-06-07

## 0a. プロジェクト基本ルール（CLAUDE.md と同期）

1. フレームワーク・言語は最新バージョン（Node 24 LTS / Python 3.14 / FastAPI / Next.js / Biome / Prettier）
2. ランタイム・ツールは **ホスト側で mise** 管理。**コンテナは公式 image** を使い、Dockerfile FROM 行と `mise.toml` で同じバージョンを書いて同期
3. 不要なライブラリは入れない（極力薄い構成）
4. dead-code は削除（未使用 export / file / dep）
5. **品質ツール**で担保: frontend = Biome + Knip、backend = Ruff、docs = Prettier

## 0. 設計の核となる判断

| 論点                | 採用                                                                                | 理由                                                                                                                                                                   |
| ------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ベクトル DB         | **PostgreSQL + pgvector**                                                           | 別サービスを足さず Docker Compose をシンプルに保てる。10K 件規模なら HNSW で十分な性能。                                                                               |
| Embedding           | **sentence-transformers `all-MiniLM-L6-v2` (384d)** をデフォルト、OpenAI を任意     | **評価者は API キーを持たない**前提。ローカルモデルでオフライン動作させ、provider 抽象で OpenAI も差し替え可能に。次元は `Settings.embedding_dim` を SSOT 化（後述）。 |
| 検索方式            | **ハイブリッド（BM25/tsvector + ベクトル）を RRF で融合**                           | セマンティックのみだと固有名詞・短いクエリに弱い。実用性のため両方を融合。                                                                                             |
| マイグレーション    | **Alembic**                                                                         | 標準。`pgvector` 拡張作成、tsvector generated column、HNSW インデックス作成すべてを Alembic で管理。                                                                   |
| 取り込み            | **`migrator` 一回限りサービス**が `alembic upgrade head` → `ingest_articles` を実行 | `docker compose up` 1 コマンドで完結させる要件を満たす。UPSERT + `content_hash` で冪等。                                                                               |
| API 設計            | **REST + Pydantic v2**、ページネーションあり                                        | OpenAPI を自動生成、frontend に型を流せる。                                                                                                                            |
| Frontend データ取得 | **TanStack Query**                                                                  | キャッシュ・楽観更新・refetch を最小コードで実現。                                                                                                                     |

## 1. ディレクトリ構成（最終形）

```
techinsight/
├── docker-compose.yml
├── docker-compose.override.yml  # 開発用: backend を --reload + bind mount（up 時に自動マージ）
├── mise.toml                    # Node / Python のバージョン定義（ホスト・Docker 共通）
├── pnpm-workspace.yaml
├── package.json                 # workspace root（prettier devDep + 統合スクリプト）
├── .prettierrc.json / .prettierignore
├── .editorconfig
├── .env.example
├── README.md                    # セットアップ・API 設計・DB 設計・工夫点を統合
├── CLAUDE.md
├── data/
│   └── articles.csv             # 既存（1,000 行）
├── docs/
│   ├── requirements.md          # 元要件
│   ├── IMPLEMENTATION_PLAN.md   # 本ファイル
│   ├── db-design.md             # 簡易 DB 設計書（成果物）
│   └── api-design.md            # 簡易 API 設計書（成果物）
├── backend/
│   ├── pyproject.toml           # uv 管理
│   ├── Dockerfile               # python:3.14.5-slim + Astral 公式 uv COPY
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py              # FastAPI エントリポイント
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings
│   │   │   ├── db.py            # AsyncSession / engine
│   │   │   └── deps.py          # DI
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── articles.py  # CRUD
│   │   │   │   ├── search.py
│   │   │   │   └── health.py
│   │   │   └── router.py
│   │   ├── models/article.py    # SQLAlchemy
│   │   ├── schemas/article.py   # Pydantic
│   │   ├── repositories/article.py
│   │   ├── services/
│   │   │   ├── embeddings/
│   │   │   │   ├── base.py
│   │   │   │   ├── local.py     # sentence-transformers
│   │   │   │   ├── openai.py
│   │   │   │   └── factory.py
│   │   │   └── search.py        # RRF 融合
│   │   └── scripts/
│   │       └── ingest_articles.py
│   └── tests/
│       ├── conftest.py          # testcontainers（本物の pgvector PG）
│       ├── test_articles_api.py
│       └── test_search.py
├── frontend/
│   ├── package.json
│   ├── biome.json               # Biome 2.x（Lint + Format + Import 並び替え）
│   ├── knip.json                # Knip（未使用 export / file / dep 検出）
│   ├── Dockerfile               # node:24.16.0-bookworm-slim + corepack 同梱 pnpm
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # 記事一覧 + 検索
│   │   └── globals.css
│   ├── components/
│   │   ├── ArticleCard.tsx
│   │   ├── ArticleModal.tsx     # 詳細 + 編集 + 削除
│   │   ├── ArticleForm.tsx      # 新規・編集共用
│   │   ├── SearchBar.tsx        # mode 切替（hybrid/keyword/semantic）
│   │   └── Pagination.tsx
│   └── lib/
│       ├── api/
│       │   ├── client.ts        # fetch wrapper
│       │   └── articles.ts      # 型付き呼び出し
│       └── hooks/
│           ├── useArticles.ts
│           └── useSearch.ts
└── .gitignore
```

## 2. DB スキーマ

```sql
-- pgvector 拡張は migration 001 で有効化
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE articles (
    id            BIGSERIAL PRIMARY KEY,
    title         TEXT        NOT NULL,
    content       TEXT        NOT NULL,
    author        TEXT        NOT NULL,
    category      TEXT        NOT NULL,
    published_at  TIMESTAMPTZ NOT NULL,
    content_hash  TEXT        NOT NULL,            -- embedding 再計算の判定用 (sha256(title || content))
    embedding     vector(384),                     -- 次元は Settings.embedding_dim で生成（下記）
    search_tsv    tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', coalesce(title,'')),   'A') ||
                    setweight(to_tsvector('english', coalesce(content,'')), 'B')
                  ) STORED,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX articles_search_tsv_idx ON articles USING GIN (search_tsv);
CREATE INDEX articles_embedding_hnsw_idx
    ON articles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX articles_category_idx     ON articles (category);
CREATE INDEX articles_published_at_idx ON articles (published_at DESC);
```

トリガで `updated_at` を自動更新。CSV の `id` は IMPORT 時に `setval` でシーケンスをずらす（新規作成時の衝突回避）。

**埋め込み次元（384）の扱い:** `vector(384)` と HNSW インデックスはハードコードせず、Alembic マイグレーションが `Settings.embedding_dim`（local=384 / OpenAI=1536）を読んで生成する（SSOT 化）。HNSW は固定次元のため、provider を切り替える場合は **DB volume 削除 → 再マイグレーション → 再 ingest** が必要（README に明記）。デフォルト local では一切意識不要。

**Alembic は async 構成:** `DATABASE_URL` は `asyncpg` ドライバ。`alembic/env.py` を `async_engine_from_config` + `run_sync` で非同期実行する（migration 用に別の sync URL を持たない、薄い構成）。`migrator` サービスが `alembic upgrade head` を実行。

## 3. API 設計（v1）

| Method | Path                    | 概要                                           |
| ------ | ----------------------- | ---------------------------------------------- | ------- | -------------------------- |
| GET    | `/health`               | ヘルスチェック（非バージョン・インフラ用）     |
| GET    | `/api/v1/articles`      | 一覧（`?page=&size=&category=&author=&sort=`） |
| GET    | `/api/v1/articles/{id}` | 単体取得                                       |
| POST   | `/api/v1/articles`      | 新規作成（embedding 自動生成）                 |
| PUT    | `/api/v1/articles/{id}` | 更新（content 変化時のみ re-embed）            |
| DELETE | `/api/v1/articles/{id}` | 削除                                           |
| GET    | `/api/v1/search`        | `?q=&mode=hybrid                               | keyword | semantic&limit=&category=` |

レスポンスは `{ items, total, page, size }` 形式。検索結果は `score` を含める（融合後の RRF スコア）。

> **`/health` について:** Docker healthcheck（compose / Dockerfile）が叩くインフラ用エンドポイントは**非バージョンの `/health`**（現状 `main.py` に実装済）に固定する。業務 API のみ `/api/v1` 配下に置く。`/api/v1/health` は設けず、healthcheck URL を壊さない。

## 4. 検索ロジック

### 4.1 キーワード

```sql
SELECT *, ts_rank(search_tsv, plainto_tsquery('english', :q)) AS score
FROM articles
WHERE search_tsv @@ plainto_tsquery('english', :q)
ORDER BY score DESC, published_at DESC
LIMIT :k;
```

### 4.2 セマンティック

```sql
SELECT *, 1 - (embedding <=> :query_vec) AS score
FROM articles
WHERE embedding IS NOT NULL
ORDER BY embedding <=> :query_vec
LIMIT :k;
```

### 4.3 ハイブリッド（RRF）

1. キーワード Top-N（例 50）とセマンティック Top-N を取得
2. 各記事の最終スコア `= Σ 1 / (k + rank)`（k=60 が定石）
3. スコア降順で limit 件返す

実装は `services/search.py`。両方の SQL を `asyncio.gather` で並列実行。

## 5. CSV 取り込み

擬似コード：

```python
async def ingest(csv_path: Path):
    embedder = get_embedder()
    rows = list(csv.DictReader(open(csv_path)))
    # 1) content_hash を計算
    # 2) DB から既存 (id, content_hash) を一括 SELECT
    # 3) 新規 or hash 変化分だけ embedding を batch 計算（model.encode に List[str] で投げる）
    # 4) INSERT ... ON CONFLICT (id) DO UPDATE で UPSERT
    # 5) シーケンスを max(id)+1 に setval
```

バッチサイズは 64〜128（メモリと速度のバランス）。`tqdm` で進捗表示（開発時のみ）。

## 6. Docker Compose 構成

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment: { POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB }
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck: pg_isready
  migrator:
    build: ./backend
    depends_on: { db: { condition: service_healthy } }
    command: >
      bash -c "alembic upgrade head &&
               python -m app.scripts.ingest_articles /app/data/articles.csv"
    volumes: ["./data:/app/data:ro"]
    restart: "no" # 一回限り
  backend:
    build: ./backend
    depends_on:
      db: { condition: service_healthy }
      migrator: { condition: service_completed_successfully }
    ports: ["8000:8000"]
  frontend:
    build: ./frontend
    depends_on: { backend: { condition: service_started } }
    environment: { NEXT_PUBLIC_API_BASE: "http://localhost:8000" }
    ports: ["3000:3000"]
volumes: { pgdata: {} }
```

> `migrator` を分離することで backend 本体は起動が速く、再起動時に重い処理が走らない。

開発時のホットリロードは `docker-compose.override.yml`（`up` 時に自動マージ）で backend に `--reload` と `./backend/app` の bind mount を付与する。本番相当で起動したい場合は `docker compose -f docker-compose.yml up` で override を無効化できる。`.venv` は image 側を使い続けるため `app/` のみを上書きする。

## 7. フロントエンド画面

- `/`: 検索バー（モード選択タブ：ハイブリッド/キーワード/セマンティック）+ カテゴリフィルタ + 記事カード一覧 + ページネーション + 「新規作成」ボタン
- 記事カードクリック → `ArticleModal` で全文表示。フッタに「編集」「削除」
- 「編集」ボタン → 同じモーダル内で `ArticleForm` にスイッチ
- 「新規作成」 → `ArticleForm` をモーダルで開く（title / content / author / category / published_at）

UX 工夫：

- 検索の debounced auto-submit（300ms）
- セマンティック検索結果に **マッチした類似度スコアをチップで表示**
- 削除時は confirm モーダル
- 楽観更新：作成・編集・削除後にローカルキャッシュを即更新

## 8. 実装フェーズ（推奨順序）

1. ~~**インフラ骨組み**~~ ✅ 完了 — `docker-compose.yml`（4 サービス）、mise ベースの backend/frontend Dockerfile、最小 FastAPI（`/health`）、`.env.example` まで。`docker compose up` で db + backend が起動し `/health` が 200 を返す状態。migrator と frontend は placeholder コマンドで定義済（次フェーズで実体化）。
   - 計画レビューに伴う微修正（2026-06-07）: `pyproject.toml` の不正な `readme` 参照を除去、backend のホットリロードを `docker-compose.override.yml` に分離（本番 compose から bind mount を撤去）、API パス方針（`/health` 非バージョン + 業務 `/api/v1`）を CLAUDE.md と同期。
2. **DB & マイグレーション** — Alembic 設定、初回 migration（pgvector 拡張 + articles テーブル + 各インデックス）。`migrator` サービスを実 alembic コマンドに差し替え。
3. **Embedding サービス** — local provider 実装 → unit test
4. **CSV 取り込みスクリプト** — 1,000 件取り込み、所要時間を計測。`migrator` で alembic 後に実行されるよう繋ぐ。
5. **Backend CRUD API** — articles ルーター + repository + pytest（httpx + testcontainers）
6. **検索 API** — keyword / semantic / hybrid 3 モード、pytest で順位検証
7. **Frontend 骨組み** — Next.js セットアップ、API クライアント、一覧表示。`frontend` サービスを `pnpm dev` に切り替え + `app/` を bind mount で HMR。
8. **検索 UI + モーダル**
9. **管理機能（作成・編集・削除）**
10. **README / DB 設計書 / API 設計書執筆**
11. **動作確認** — クリーンクローン → `docker compose up` → 全機能 E2E 手動チェック

## 9. テスト方針

- **Backend:** pytest + httpx（API 統合）。DB は testcontainers-python で**本物の pgvector PostgreSQL** を立てる（sqlite は pgvector / tsvector 非対応のため fallback しない）。RRF 融合は純粋関数として切り出し、DB 非依存の単体テストで順位を検証する。Embedding は `LocalEmbedder` を deterministic な mock に差し替えてベクトル検索のロジックを検証。テスト用 dev 依存（`pytest-asyncio` / `testcontainers` 等）はテストフェーズで追加。
- **Frontend:** Vitest で hook / component のユニット。E2E は時間が余れば Playwright で「新規作成 → 一覧反映 → 検索ヒット → 編集 → 削除」を一本通す。
- **CI（任意）:** GitHub Actions で lint + test。本人開発だが「チーム開発を意識」要件への布石。

## 10. 提出物チェックリスト

- [ ] Public GitHub リポジトリ
- [ ] README（セットアップ、起動、トラブルシュート、機能紹介、工夫点）
- [ ] `docs/db-design.md`（簡易 DB 設計書）
- [ ] `docs/api-design.md`（簡易 API 設計書）
- [ ] 実装説明（UI/UX / DB / チーム開発 / 保守運用・スケーラビリティ / その他）— README 末尾に統合可
- [ ] `docker compose up` 1 コマンドで全機能動作
- [ ] `.env.example` あり、`.env` は gitignore
- [ ] API キー不要で完全動作（OpenAI は任意）

## 11. リスクと対策

| リスク                                                                  | 対策                                                                                                                                                                                                                                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Python 3.14 で torch/sentence-transformers が入らない**（最大リスク） | **検証済み（2026-06-07）**: torch 2.12.0 は cp314 wheel を linux x86_64 / aarch64 / macOS arm64 向けに配布、transformers は pure-python、tokenizers は abi3 wheel。**Python 3.14 + ローカル埋め込みは成立**。lockfile（`uv.lock`）で固定し再現性を担保                    |
| torch 同梱による backend イメージ肥大・ビルド遅延                       | torch + モデル焼き込みで数百 MB〜GB 級になるのは許容。`uv sync` のレイヤキャッシュ + モデル焼き込みで**2 回目以降の `up` は高速**。CPU 版 torch のみ（CUDA 不要）で抑える                                                                                                 |
| sentence-transformers の初回モデルダウンロードが遅い                    | Dockerfile の build 時に `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` でイメージに焼き込む。**`HF_HOME` を `app` ユーザ書込可能パスに設定**し、build 時 cache と実行時 cache を一致させて再 DL を防ぐ |
| CSV 取り込みでメモリ不足                                                | バッチ embedding + chunk insert（CSV 全行をメモリに載せない設計）                                                                                                                                                                                                         |
| Apple Silicon vs x86 の image 差異                                      | `pgvector/pgvector:pg16` は両対応、Python 系も slim-bookworm を使用。torch cp314 も両アーキの wheel あり（検証済）                                                                                                                                                        |
| HNSW インデックスの構築時間                                             | 1 万件程度なら数秒〜数十秒。INSERT 後に再構築せずインデックス先張りで OK                                                                                                                                                                                                  |
| OpenAI 切り替え時の次元不一致（384 vs 1536）                            | 次元は `Settings.embedding_dim` を SSOT 化し、マイグレーションがこの値でカラム・HNSW を生成。HNSW は固定次元のため切替には **volume 削除 → 再マイグレーション → 再 ingest** が必要 — README に明記。デフォルト local では無関係                                           |
