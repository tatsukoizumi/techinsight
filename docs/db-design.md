# DB 設計書

TechInsight のデータベース設計をまとめる。RDBMS は **PostgreSQL 16 + pgvector 拡張**。
スキーマは Alembic マイグレーション（`backend/alembic/versions/0001_initial.py`）で一元管理する。

## ER 概要

エンティティは記事 1 種類のみ（`articles`）。検索インデックスとベクトル列を同一テーブルに
持たせることで、キーワード検索・セマンティック検索・CRUD をすべて 1 テーブルで完結させる。

## テーブル: `articles`

| カラム         | 型            | 制約 / 既定値                    | 説明                                                          |
| -------------- | ------------- | -------------------------------- | ------------------------------------------------------------- |
| `id`           | `BIGSERIAL`   | PRIMARY KEY                      | 記事 ID。CSV の id をそのまま採用し、取り込み後に採番をずらす |
| `title`        | `TEXT`        | NOT NULL                         | タイトル                                                      |
| `content`      | `TEXT`        | NOT NULL                         | 本文                                                          |
| `author`       | `TEXT`        | NOT NULL                         | 著者                                                          |
| `category`     | `TEXT`        | NOT NULL                         | カテゴリ（Backend / DevOps / AI/ML / Frontend …）             |
| `published_at` | `TIMESTAMPTZ` | NOT NULL                         | 公開日時                                                      |
| `content_hash` | `TEXT`        | NOT NULL                         | `sha256(title + content)`。embedding 再計算要否の判定に使う   |
| `embedding`    | `vector(N)`   | NULL 許容                        | 本文の埋め込み。次元 N は provider で決まる（local=384）      |
| `search_tsv`   | `tsvector`    | GENERATED ALWAYS … STORED        | `title`(A) + `content`(B) の全文検索ベクトル（自動生成列）    |
| `created_at`   | `TIMESTAMPTZ` | NOT NULL DEFAULT now()           | 作成日時                                                      |
| `updated_at`   | `TIMESTAMPTZ` | NOT NULL DEFAULT now()（トリガ） | 更新日時。`BEFORE UPDATE` トリガで自動更新                    |

### 生成列 `search_tsv`

```sql
setweight(to_tsvector('english', coalesce(title,   '')), 'A') ||
setweight(to_tsvector('english', coalesce(content, '')), 'B')
```

タイトルに重み A、本文に重み B を与え、タイトル一致を上位に出やすくする。アプリ側で
更新する必要がない STORED 生成列とすることで、データ不整合を防ぐ。

## インデックス設計

10K 件規模でも検索を必ずインデックス経由にするため、用途ごとに張り分ける。

| インデックス                  | 種類          | 対象                          | 用途                           |
| ----------------------------- | ------------- | ----------------------------- | ------------------------------ |
| `articles_pkey`               | B-tree        | `id`                          | 主キー / 単体取得・UPSERT      |
| `articles_search_tsv_idx`     | **GIN**       | `search_tsv`                  | キーワード検索（全文検索）     |
| `articles_embedding_hnsw_idx` | **HNSW**      | `embedding vector_cosine_ops` | セマンティック検索（コサイン） |
| `articles_category_idx`       | B-tree        | `category`                    | カテゴリ絞り込み               |
| `articles_published_at_idx`   | B-tree (DESC) | `published_at`                | 新着順ソート                   |

- **HNSW** は近似最近傍探索で、1 万件規模なら数秒〜数十秒で構築でき、検索は数 ms。
- HNSW は**固定次元**のため、provider 切替（local 384 ↔ OpenAI 1536）時は
  **DB ボリューム削除 → 再マイグレーション → 再取り込み**が必要（README 参照）。

## 埋め込み次元の SSOT 化

`vector(N)` の N と HNSW インデックスはハードコードせず、`Settings.embedding_dim`
（`backend/app/core/config.py`）を唯一の真実とし、マイグレーションがこの値を読んで
DDL を生成する。デフォルト（local / 384 次元）では一切意識不要。

## 冪等な取り込み

`backend/app/scripts/ingest_articles.py` が CSV を取り込む。`id` で UPSERT し、
`content_hash` が変化したレコードのみ embedding を再計算するため、再実行しても
全件再計算は走らない（10K スケールを考慮）。取り込み後に
`setval('articles_id_seq', max(id))` で採番を進め、新規作成時の id 衝突を防ぐ。

## マイグレーション方針

- スキーマ変更はすべて Alembic（手動 SQL は使わない）。
- pgvector 拡張の有効化（`CREATE EXTENSION IF NOT EXISTS vector`）も最初の
  マイグレーションで実施。
- `alembic/env.py` は asyncpg ドライバで非同期実行する構成（sync 用 URL を別途持たない）。
