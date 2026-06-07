---
name: reingest-csv
description: 記事 CSV（data/articles.csv）を DB に（再）取り込むときの手順。idempotent な UPSERT と content_hash による embedding 差分再計算の仕組みを含む。CSV を更新した・記事データを入れ直したい・embedding を作り直したいといった依頼で使う。
---

# CSV を（再）取り込む

取り込みは `app/scripts/ingest_articles.py`（参照: `backend/app/scripts/ingest_articles.py`）。**idempotent** に設計されている:

- ID で **UPSERT**（既存レコードは更新、新規は挿入）。
- `content_hash` が変わったレコードのみ **embedding を再計算**（10K スケールで全件再計算を避けるため）。
- 初回 `docker compose up` では `migrator` サービスが `alembic upgrade head` → ingest を自動実行する。

## 実行方法

通常はワンショットの `migrator` を再実行するのが簡単:

```bash
docker compose run --rm migrator
```

スクリプトを直接叩く場合（引数に CSV パスが**必須**、1 引数のみ）:

```bash
docker compose run --rm backend python -m app.scripts.ingest_articles /data/articles.csv
```

ローカル backend で動かす場合は DB を先に起動（`docker compose up -d db`）してから同コマンド。

## 注意

- **embedding を全部作り直したい**とき（例: provider を local ↔ openai に切替）は、次元が変わるため再取り込みだけでは不十分。**`docker compose down -v` で DB volume を削除 → `up` で再マイグレーション → 自動 ingest**（詳細は add-migration スキル）。
- CSV のスキーマ（列）を変える場合は ORM / マイグレーションの整合も確認する。
- `data/*.csv` はコミットしない方針（`.gitignore` 参照）。シークレットや個人情報を含む CSV を持ち込まない。

## 確認

- backend ログ（`docker compose logs migrator` / `backend`）で取り込み件数・エラーを確認。
- `curl -fsS http://localhost:8000/health` と記事一覧 API で反映を確認。
