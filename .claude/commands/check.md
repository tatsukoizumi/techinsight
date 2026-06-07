---
description: lint / format / dead-code / テストを領域別に回し、失敗は修正まで仕上げる
argument-hint: "[frontend | backend | all（既定）]"
allowed-tools: Bash, Read, Edit
---

# /check

品質ゲートをまとめて実行し、**通るまで仕上げる**コマンド。CI（`.github/workflows/ci.yml`）と同じチェックをローカルで先回りするのが目的。

引数 `$ARGUMENTS` で対象を絞る（省略時は `all`）:

- `frontend` … Biome + Knip
- `backend` … Ruff + pytest
- `all` … 上記すべて + docs（Prettier）

## 手順

### frontend（`frontend` または `all`）

1. `pnpm fe:quality`（= Biome check + Knip）を実行。
2. 失敗したら:
   - format / lint の自動修正可能分は `pnpm fe:check:fix` で修正。
   - Knip の未使用 export / file / dep は**該当コードを削除**して解消（CLAUDE.md「dead-code は削除する」）。安易に knip.json で握りつぶさない。
3. 再実行して green を確認。

### backend（`backend` または `all`）

1. `cd backend && uv run ruff check . && uv run ruff format --check .` を実行。
2. 失敗したら `uv run ruff check --fix .` と `uv run ruff format .` で修正（残る指摘は手で対応）。
3. `cd backend && uv run pytest` を実行（testcontainers が pgvector を起動するため Docker が必要）。
4. テスト失敗は原因を読み解いて修正する。テストを安易に skip / xfail しない。

### docs（`all` のみ）

1. `pnpm format:check`（Prettier: Markdown / YAML / root JSON）。
2. 失敗したら `pnpm format` で整形。

## 原則

- **緑になるまで終わらない**。「警告が出たが続行」はしない。
- 自動修正で消えない指摘は、握りつぶさず根本対応する。
- 修正で差分が出たら、コミットは `/commit` に委ねる（このコマンドはコミットしない）。

引数: $ARGUMENTS
