# API 設計書

TechInsight バックエンドの REST API 仕様。実装は FastAPI + Pydantic v2。
OpenAPI ドキュメントは起動後 `http://localhost:8000/docs`（Swagger UI）で確認できる。

## 方針

- 業務 API はすべて **`/api/v1`** 配下にバージョニングする。
- インフラ用ヘルスチェックのみ非バージョンの **`/health`**（Docker healthcheck が叩く URL を固定）。
- レスポンスは JSON。一覧は `{ items, total, page, size }`、検索は `{ items, total, mode, query }`。
- エラーは FastAPI 標準（`{ "detail": ... }`、バリデーションは 422）。

## エンドポイント一覧

| Method | パス                    | 概要                                           |
| ------ | ----------------------- | ---------------------------------------------- |
| GET    | `/health`               | ヘルスチェック（非バージョン）                 |
| GET    | `/api/v1/articles`      | 記事一覧（ページネーション・絞り込み・ソート） |
| GET    | `/api/v1/articles/{id}` | 記事単体取得                                   |
| POST   | `/api/v1/articles`      | 記事作成（embedding 自動生成）                 |
| PUT    | `/api/v1/articles/{id}` | 記事更新（content 変化時のみ再 embed）         |
| DELETE | `/api/v1/articles/{id}` | 記事削除                                       |
| GET    | `/api/v1/search`        | 検索（hybrid / keyword / semantic）            |

## モデル

### Article（レスポンス）

```json
{
  "id": 1,
  "title": "string",
  "content": "string",
  "author": "string",
  "category": "string",
  "published_at": "2025-09-19T22:00:00Z",
  "created_at": "2026-06-07T00:00:00Z",
  "updated_at": "2026-06-07T00:00:00Z"
}
```

内部列（`embedding` / `content_hash` / `search_tsv`）はレスポンスに含めない。

### ArticleCreate / ArticleUpdate（リクエスト）

- 作成: `title` / `content` / `author` / `category` / `published_at` すべて必須（空文字不可）。
- 更新: 全フィールド任意（部分更新）。指定したフィールドのみ変更。

## エンドポイント詳細

### `GET /api/v1/articles`

クエリパラメータ:

| 名前       | 型     | 既定値   | 説明                               |
| ---------- | ------ | -------- | ---------------------------------- |
| `page`     | int    | 1        | 1 始まりのページ番号（≥1）         |
| `size`     | int    | 20       | 1 ページ件数（1–100）              |
| `category` | string | —        | カテゴリ完全一致で絞り込み         |
| `author`   | string | —        | 著者完全一致で絞り込み             |
| `sort`     | enum   | `newest` | `newest`（公開日時降順）/ `oldest` |

レスポンス: `{ items: Article[], total, page, size }`

### `POST /api/v1/articles`

リクエストボディ = ArticleCreate。サーバが本文から embedding を生成し、`content_hash` を
計算して保存する（embedding 計算は CPU バウンドのためスレッドプールに逃がす）。
レスポンス 201 + 作成された Article。

### `PUT /api/v1/articles/{id}`

リクエストボディ = ArticleUpdate（部分更新）。`content` が変化した場合のみ embedding を
再生成する。`title` または `content` が変化したら `content_hash` を更新。404 if 存在しない。

### `DELETE /api/v1/articles/{id}`

成功時 204。404 if 存在しない。

### `GET /api/v1/search`

クエリパラメータ:

| 名前       | 型     | 既定値   | 説明                              |
| ---------- | ------ | -------- | --------------------------------- |
| `q`        | string | （必須） | 検索クエリ（1 文字以上）          |
| `mode`     | enum   | `hybrid` | `hybrid` / `keyword` / `semantic` |
| `limit`    | int    | 20       | 返却件数（1–100）                 |
| `category` | string | —        | カテゴリ絞り込み                  |

レスポンス: `{ items: (Article & { score })[], total, mode, query }`。`score` は

- `keyword`: `ts_rank`（PostgreSQL 全文検索スコア）
- `semantic`: コサイン類似度（`1 - (embedding <=> query_vec)`）
- `hybrid`: RRF（Reciprocal Rank Fusion）スコア

### 検索モードの仕組み

1. **keyword**: `tsvector @@ plainto_tsquery` を GIN インデックスで評価し `ts_rank` 順。
2. **semantic**: クエリを埋め込みベクトル化し、pgvector の HNSW でコサイン近傍探索。
3. **hybrid**: 上記 2 つの上位候補（各 50 件）を取得し、**RRF（k=60）** で順位を融合。
   `score = Σ 1 / (k + rank)`。固有名詞・短いクエリに強いキーワード検索と、言い換えに
   強いセマンティック検索の長所を両取りする。

## ステータスコード

| コード | 意味                                       |
| ------ | ------------------------------------------ |
| 200    | 取得・更新・検索成功                       |
| 201    | 作成成功                                   |
| 204    | 削除成功（ボディなし）                     |
| 404    | 対象が存在しない                           |
| 422    | バリデーションエラー（必須欠落・型不正等） |
