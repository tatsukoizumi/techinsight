# 開発・運用ガイド

ローカル開発、テスト、品質保証、CI/CD、依存管理の運用方針をまとめる。
プロダクトの設計判断は [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)、
DB / API 仕様は [`db-design.md`](db-design.md) / [`api-design.md`](api-design.md) を参照。

## 設計思想: 薄い構成を保つ

「便利そうだから」での依存追加をしない。標準ライブラリ・既存ツールで済むものは増やさず、
未使用の export / file / dependency は仕組みで検出して消す。具体的には:

- **状態管理ライブラリを入れない** — サーバ状態は TanStack Query、UI 状態は React 標準（`useState` /
  URL クエリ）で完結させ、Redux/Zustand 等を持ち込まない。
- **UI コンポーネントは shadcn/ui 方式** — npm パッケージとして抱えず、必要な Radix プリミティブの上に
  最小限のコンポーネント（`components/ui/`）を**自前のソースとして配置**。使う分だけを持ち、
  バンドルと依存ツリーを薄く保つ。
- **dead-code を残さない** — frontend は **Knip** で未使用 export / file / dep を検出。機能を消したら関連も同時に消す。
- **AI エージェント設定も最小限** — `.claude/` 配下の hooks / commands / skills は、品質を「人間の規律」ではなく
  「仕組み」で担保するための薄い設定のみ。詳細は後述。

## ツールバージョン管理: mise

ホスト側のランタイム / ツールのバージョンは [mise](https://mise.jdx.dev/) の `mise.toml` を
**単一の真実（SSOT）**とする。

```bash
mise install   # Node 24.16.0 / Python 3.14.5 / uv / pnpm 11.5.2 を取得
pnpm install   # workspace 全体（root + frontend）
```

- `pnpm` も mise 管理とし、`package.json` の `packageManager` フィールドと同期する。
- **コンテナ内には mise レイヤを挟まない。** 公式 image（`python:3.14.5-slim` / `node:24.16.0-bookworm-slim` /
  `pgvector/pgvector:pg16`）を使い、Dockerfile の `FROM` 行に `mise.toml` と同じバージョンを書いて手動同期する。
  バージョンを上げるときは `mise.toml` と Dockerfile を**同じ PR で**更新する。
- CI も [`jdx/mise-action`](https://github.com/jdx/mise-action) で同じ `mise.toml` を読むため、
  ローカル・CI・コンテナのバージョンが一致する。

## ローカル開発

```bash
# バックエンドのみ（DB はコンテナ、API はホットリロード）
docker compose up -d db
cd backend && uv sync && uv run uvicorn app.main:app --reload

# フロントエンドのみ
pnpm fe:dev

# CSV 再取り込み（idempotent: 既存は UPSERT、content_hash 変化分のみ再 embed）
docker compose run --rm migrator
```

## テスト

```bash
cd backend && uv run pytest         # 全テスト
pnpm --filter frontend test         # Vitest
```

backend のテストは **testcontainers で本物の pgvector PostgreSQL を起動**して実行する。
sqlite を使わないのは、`tsvector`（全文検索）/ `vector`（pgvector）が sqlite 非対応であり、
**本番と同じエンジンでなければ検索順位の検証に意味がない**ため。キーワード／セマンティック検索の
ランキングを実 DB に対して検証する。

## 品質チェック

役割が重複しないようツールを分担する。

| 対象                        | ツール                           | コマンド                                      |
| --------------------------- | -------------------------------- | --------------------------------------------- |
| Frontend (TS/TSX)           | Biome（Lint+Format+Import 整列） | `pnpm fe:check` / `pnpm fe:check:fix`         |
| Frontend dead-code          | Knip                             | `pnpm fe:knip`                                |
| Markdown / YAML / root JSON | Prettier                         | `pnpm format:check` / `pnpm format`           |
| Backend (Python)            | Ruff（Lint+Format）              | `uv run ruff check . && uv run ruff format .` |

```bash
pnpm quality   # Prettier --check + Biome + Knip（frontend 全部）
pnpm check     # Prettier + Biome のみ（dead-code 除く、速い）
pnpm fix       # 自動修正
```

`.prettierignore` で `frontend/` を除外し、Prettier（docs 用）と Biome（frontend 用）の責務が
重ならないようにしている。

### AI エージェント Hook による自動整形

`.claude/settings.json` の `PostToolUse` hook が、AI エージェントが Edit/Write した直後に
**該当ファイルだけ**を拡張子でルーティングして整形 + lint する（frontend→Biome / backend→Ruff /
docs→Prettier）。自動修正で消えない指摘は exit 2 で差し戻し、エージェントに自己修正させる。
Knip は全体解析のため hook には含めず、`pnpm quality`・CI に委譲する。

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) が PR と main への push で 3 ジョブを並列実行する。

| ジョブ             | 内容                                        |
| ------------------ | ------------------------------------------- |
| `frontend-quality` | `pnpm quality`（Prettier + Biome + Knip）   |
| `backend-quality`  | Ruff（lint + format --check）               |
| `backend-test`     | pytest（testcontainers で pgvector を起動） |

- `jdx/mise-action` で `mise.toml` をバージョンの単一ソースにし、ローカルと同条件で回す。
- `concurrency` で同一ブランチの古い実行をキャンセルし、無駄な CI を省く。

## 依存の自動更新と脆弱性監査

### Dependabot

[`.github/dependabot.yml`](../.github/dependabot.yml) で毎週月曜にまとめて更新 PR を作る。
ノイズを抑えるため **ecosystem ごとに 1 PR へグルーピング**している。

| ecosystem        | 対象                           | PR prefix |
| ---------------- | ------------------------------ | --------- |
| `npm`            | frontend（pnpm workspace）     | `build`   |
| `uv`             | backend（pyproject + uv.lock） | `build`   |
| `github-actions` | CI で使う action               | `ci`      |

> Docker image は対象外。コンテナのバージョンは `mise.toml` と Dockerfile を手動同期する運用のため、
> 自動バンプしない（CLAUDE.md 基本ルール 2）。

### 脆弱性監査 — `/audit`

依存の脆弱性監査は `.claude/commands/audit.md`（`/audit` コマンド）に手順を定義し、
**恒久依存を増やさずに**実行する。

- **frontend:** `pnpm audit`（必要に応じ `--json`）で advisory を確認し、単純なアップデートで
  解消できるものを解消 → `pnpm fe:quality` / `pnpm fe:build` で回帰確認。
- **backend:** uv に監査は組み込まれていないため、`uvx` で **`pip-audit` をエフェメラル実行**する。
  `uv export` で requirements を書き出して `uvx pip-audit -r ...`。監査ツールを依存に常駐させない。

## ブランチ運用

- `main` は**保護ブランチ**。直接 push を禁止し、**PR 経由 + CI グリーン**を必須とする。
- コミットは [Conventional Commits](https://www.conventionalcommits.org/)（`feat` / `fix` / `build` / `ci` / `style` …）。
- スキーマ変更は Alembic 一元管理（手動 SQL を使わない）。詳細は [`db-design.md`](db-design.md)。
