---
name: add-api-endpoint
description: TechInsight のバックエンドに新しい API エンドポイント / リソースを追加するときの定型手順。レイヤリング（api → schemas → services → repositories → models）と testcontainers ベースの統合テストの書き方を含む。FastAPI ルーターや CRUD・検索系の API を増やす依頼で使う。
---

# 新しい API エンドポイントを追加する

`backend/app/` のレイヤリングを上から下へ守って追加する。既存の `articles` リソースが参照実装。

## レイヤの責務（薄い順に）

1. `app/api/v1/<resource>.py` — FastAPI ルーター。**薄く保つ**。I/O は Pydantic スキーマのみ、ロジックは service に委譲。`app/api/router.py` に `include_router` で登録。
2. `app/schemas/<resource>.py` — Pydantic v2 のリクエスト / レスポンス。ORM とは分離。
3. `app/services/<resource>.py` — ビジネスロジック（検索融合、embedding 生成など）。CPU バウンドな embedding 計算は `run_in_threadpool` で逃がす。
4. `app/repositories/<resource>.py` — SQLAlchemy クエリ。テスト容易化のため抽象化。N+1 を避け、必要なら `selectinload`。
5. `app/models/<resource>.py` — SQLAlchemy ORM。スキーマ変更を伴うなら **add-migration スキルでマイグレーションを追加**（手書き SQL 禁止）。

依存（DB セッション・embedder）は `app/core/deps.py` 経由で注入する。

## 参照実装

- ルーター: `backend/app/api/v1/articles.py` / `backend/app/api/v1/search.py`
- サービス: `backend/app/services/articles.py` / `backend/app/services/search.py`
- リポジトリ: `backend/app/repositories/article.py`

## テスト（必須）

`backend/tests/` に統合テストを追加する。`conftest.py` が **testcontainers で実際の pgvector PostgreSQL** を起動し、`client`（依存オーバーライド済み AsyncClient）と `fake_embedder`（決定論的）フィクスチャを提供する。`test_articles_api.py` に倣い、CRUD・ページネーション・バリデーション・404 を網羅する。モックではなく実 DB で `tsvector` / `vector` インデックスを通すこと。

## 仕上げ

- `cd backend && uv run pytest` が green。
- `/check backend`（Ruff + pytest）を通す。
- API 仕様を変えたら `docs/api-design.md` を更新。
- 区切りごとに `/commit`（`feat(backend): ...`）。
