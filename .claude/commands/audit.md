---
description: 依存パッケージの脆弱性を監査し、単純なアップデートで解消できるものは解消する
argument-hint: "[frontend | backend | all（既定）]"
allowed-tools: Bash, Read, Edit
---

# /audit

依存パッケージの既知脆弱性を監査し、**解消する**コマンド。方針:

- **シンプルな対応を優先**する。単純なパッケージのアップデート（直接依存の patch / minor バンプ）で解消できるものは**そのまま実行**する。
- **override 等の複雑な対応が必要な場合は、適用前にユーザーへ許可を求める**（破壊的アップデート、`pnpm.overrides` / uv の constraint 追加、major バンプ、修正版が未リリース、など）。

引数 `$ARGUMENTS` で対象を絞る（省略時は `all`）: `frontend` / `backend` / `all`。

> 監査はオンライン advisory DB（npm / PyPI / OSV）を参照するためネットワークが必要。取得失敗時はその旨を報告して中断する。

## frontend（pnpm）

1. **監査**: `pnpm audit`（vuln があると exit が非 0 になるが、エラー扱いせず内容を読む）。重大度の高い順に整理し、各 advisory の「脆弱なパッケージ / 経路（直接 or 推移的依存）/ 修正バージョン」を把握する。詳細が要るときは `pnpm audit --json`。
2. **解消の判断**:
   - **直接依存**（`frontend/package.json` に載っている）で、semver 範囲内 or patch/minor で修正版がある → **シンプル**。`pnpm --filter frontend update <pkg>` で更新（必要なら `frontend/package.json` の version を patch/minor だけ引き上げてから `pnpm install`）。
   - **推移的依存**（直接は無く lockfile 経由）→ 修正には通常 `pnpm.overrides`（package.json）が必要 = **複雑**。**ユーザーに許可を求めてから** override を追加する（追加するパッケージ名・固定バージョンを提示する）。
   - **major バンプ / 破壊的変更が必要** → **複雑**。許可を求める。
3. **適用後**: `pnpm install` → `pnpm audit` を再実行して解消を確認。`pnpm fe:quality`（Biome + Knip）と、可能なら `pnpm fe:build` で回帰がないことを確認。

## backend（uv + pip-audit）

uv には監査が組み込まれていないため、**`uvx` で `pip-audit` をエフェメラル実行**する（恒久依存は追加しない）。

1. **監査**:
   ```bash
   cd backend
   uv export --no-emit-project --format requirements-txt -o /tmp/ti-audit-reqs.txt
   uvx pip-audit -r /tmp/ti-audit-reqs.txt
   ```
   各 advisory の「パッケージ / 現在バージョン / 修正バージョン / 直接 or 推移的依存」を把握する。
2. **解消の判断**:
   - **直接依存**（`backend/pyproject.toml` の `dependencies` / `dev` に載っている）で patch/minor で修正版がある → **シンプル**。pyproject.toml の下限を修正版以上に引き上げ（例 `fastapi>=0.115` → `fastapi>=0.115.x`）、`uv lock` → `uv sync` で反映。
   - **推移的依存**（pyproject に無く lockfile 経由）→ ピン留めには `[tool.uv] constraint-dependencies`（または `override-dependencies`）が必要 = **複雑**。**ユーザーに許可を求めてから**追加する。
   - **major バンプ / 修正版が未リリース** → **複雑**。許可を求める。`torch` など重量級の major バンプは特に慎重に。
3. **適用後**: `uv export ... && uvx pip-audit -r ...` を再実行して解消を確認。`/check backend`（Ruff + pytest）で回帰がないことを確認。後片付けに `/tmp/ti-audit-reqs.txt` を削除。

## 原則

- **直さない判断も明示する**: 修正版が無い / dev・テスト専用で実害が低い / 破壊的すぎる場合は、無理に直さず**状況と推奨を報告**してユーザーに委ねる。握りつぶさない。
- **1 つずつ確実に**: 複数の脆弱性があれば優先度（critical → high → …）順に、1 件直すごとに再監査して効果を確認する。
- **コミットは分ける**: 解消後の変更は `/commit`（`fix(deps): ...` 等）に委ねる。このコマンドはコミットしない。

## 報告フォーマット（最後に必ず出す）

- 監査結果サマリ（重大度別の件数、frontend / backend 別）
- 自動で解消したもの（パッケージ・before→after バージョン）
- ユーザー判断待ち（override や major バンプが必要なもの）
- 直さなかったもの（理由つき）

引数: $ARGUMENTS
