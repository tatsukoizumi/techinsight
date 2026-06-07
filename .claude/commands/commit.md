---
description: 差分を過不足なくステージング・必要に応じて分割し、簡潔な英語メッセージで commit する
argument-hint: "[任意: 追加指示。例: 'setup までで切って' / 'docs だけ別 commit'] "
allowed-tools: Bash, Read, Edit
---

# /commit

現在の作業ツリーを過不足なく git commit する。下記の原則を厳守すること。

## 原則

### 1. 過不足なく commit する

- **漏らさない**: `git status` で untracked を含む全変更を確認する。stage 漏れを残してはいけない。
- **混ぜない**: 関連性のない変更が同じ作業ツリーに混在していたら **論理的に分割して複数 commit** にする（例: 機能追加と、それと無関係な lint 修正は別 commit）。
- **危険なものは入れない**: `.env` / `*.key` / `id_rsa` / `credentials.*` / 巨大バイナリ / 個人情報を含むファイルは絶対にステージしない。疑わしい場合はユーザーに確認する。
- **明示的に add する**: `git add -A` / `git add .` は使わず、ファイル名を列挙して `git add <files...>` する。

### 2. コミットメッセージ（英語、簡潔）

- **subject（1 行目）**:
  - 50〜72 文字以内
  - **命令形・現在形**で書く（"Add X" / "Fix Y" / "Refactor Z" / "Remove W"）
  - 文末にピリオドを付けない
  - 大文字始まり（type プレフィックスを除く）
  - **Conventional Commits 形式**を採用: `<type>(<scope>): <subject>`
    - type: `feat` / `fix` / `refactor` / `chore` / `docs` / `test` / `style` / `perf` / `ci` / `build`
    - scope（任意）: `backend` / `frontend` / `db` / `docker` / `ci` / `deps` など、変更領域
- **body（本文、必要な場合のみ)**:
  - subject から空行 1 行あけて記述
  - **why** を書く（"what" は diff から読める）
  - 72 文字で改行
  - 箇条書きは `-` を使う
- **footer は付けない**: AI 共同著者・自動生成タグは含めない（コーディング試験の文脈のため）。

良い例:

```
feat(backend): add semantic search endpoint

Implements hybrid search combining BM25 (tsvector) and pgvector
cosine similarity, merged via Reciprocal Rank Fusion. Required for
the search API milestone.
```

```
chore(docker): pin frontend port to env override
```

```
fix(frontend): handle empty search results
```

悪い例:

- `update files`（情報量ゼロ）
- `Fixed the bug.`（過去形・ピリオド）
- `feat: 検索 API を追加した`（日本語）
- `feat(backend): add semantic search endpoint and also bump prettier and update README` （複数の関心事が一文に）

### 3. 手順

1. **状況把握**（並列実行）:
   - `git status`（untracked を含めて全変更を確認）
   - `git diff`（unstaged 差分の内容）
   - `git diff --staged`（既にステージ済みのものがあるか）
   - `git log --oneline -10`（既存スタイル確認。コミットがゼロなら Conventional Commits を採用）
2. **分析**:
   - 機密ファイル混入の有無を最初にチェック
   - 論理的に 1 commit か複数 commit かを判断（迷ったら **分ける** 方を選ぶ）
   - 各 commit の subject 行をドラフト（必要なら body も）
3. **ステージ & コミット**:
   - `git add <files>` で明示的に add
   - HEREDOC でメッセージを渡して `git commit` 実行:

     ```
     git commit -m "$(cat <<'EOF'
     feat(scope): short subject

     Optional body explaining why, wrapped at 72 chars.
     EOF
     )"
     ```

   - 複数 commit が必要な場合は 1 つずつ完了させてから次へ

4. **検証**:
   - `git status` で working tree が想定通り（残すべき untracked は残る、コミットすべきは消える）
   - `git log --oneline -<n>` で直近の n commit を確認

### 4. エッジケース

- **コミット対象なし**: untracked / 変更が無ければ何もせず「変更なし」と報告する。空 commit は作らない。
- **pre-commit hook 失敗**: 失敗時はコミットは実行されていない。原因を読み解いて修正（lint なら自動修正、テスト失敗なら原因対応）→ 再度 add → **新規 commit を作る**（`--amend` は使わない、`--no-verify` も使わない）。
- **巨大ファイル検出**: 100MB を超える、または明らかにビルド成果物（`node_modules/` `.next/` `dist/` など）が紛れていたら、ステージせずユーザーに警告。
- **git リポジトリでない**: 親ディレクトリも含めて `.git` がなければ「git 未初期化です。`git init` しますか？」と確認してから進む。
- **push しない**: 明示的に指示がない限り `git push` は実行しない。

## 引数

ユーザーが `/commit $ARGUMENTS` の形で追加指示を与えた場合、その指示を上記原則より **優先する**（例: 「全部 1 commit にして」「scope は frontend で固定」など）。引数が空ならデフォルト挙動。

引数: $ARGUMENTS
