---
name: add-migration
description: TechInsight の DB スキーマ変更を Alembic マイグレーションで行うときの手順。autogenerate → 確認 → upgrade の流れと、embedding 次元（Settings.embedding_dim が SSOT）・pgvector HNSW にまつわる落とし穴を含む。ORM モデルやカラム・インデックスを変更する依頼で使う。
---

# Alembic マイグレーションを追加する

スキーマ変更は **必ず Alembic 一本化**。手書き SQL を別経路で流さない。pgvector 拡張の有効化も Alembic で（`CREATE EXTENSION IF NOT EXISTS vector`）。既存: `backend/alembic/versions/0001_initial.py`。

## 手順

1. まず `app/models/` の ORM を変更する。
2. DB を起動: `docker compose up -d db`。
3. 自動生成:
   ```bash
   cd backend && uv run alembic revision --autogenerate -m "<説明>"
   ```
4. **生成された `backend/alembic/versions/<id>_*.py` を必ず目視確認**する。autogenerate は pgvector の `vector` 型・HNSW / GIN インデックス・generated column（`search_tsv`）を取りこぼすことがある。欠けていれば手で `op.execute(...)` / `op.create_index(...)` を補う。
5. 適用: `cd backend && uv run alembic upgrade head`。
6. ダウングレード（`downgrade`）も成立するか確認。

## 落とし穴（重要）

- **embedding 次元は `Settings.embedding_dim` が SSOT**（`backend/app/core/config.py`、local=384 / openai=1536）。`embedding` カラムと HNSW インデックスはこの値から生成する。次元をハードコードしない。
- **HNSW は固定次元**。provider を local ↔ openai で切り替えると次元が変わるため、マイグレーションだけでは追従できない。切替時は **DB volume 削除 → 再マイグレーション → 再 ingest** が必要（`docker compose down -v` → `up`）。この前提を壊す変更をしない。
- インデックス設計を維持: `embedding` は `USING hnsw (embedding vector_cosine_ops)`、`search_tsv` は GIN、`category` / `published_at` は B-tree。

## 仕上げ

- `cd backend && uv run pytest`（conftest が実 pgvector にマイグレーションを流すので、壊れていれば落ちる）。
- スキーマを変えたら `docs/db-design.md` を更新。
- `/commit`（`feat(db): ...`）。マイグレーションファイルと ORM 変更は同じ commit に。
