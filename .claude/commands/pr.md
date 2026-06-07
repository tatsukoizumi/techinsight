---
description: 現ブランチの差分から Conventional Commits 準拠の PR を gh で作成する
argument-hint: "[任意: 追加指示。例: 'draft で' / 'base を develop に']"
allowed-tools: Bash, Read
---

# /pr

現在のブランチを GitHub に push し、`gh pr create` で Pull Request を作成する。
コミット規約は `/commit`（`.claude/commands/commit.md`）と揃える。

## 前提チェック

1. `git rev-parse --abbrev-ref HEAD` で現ブランチを確認。**`main` の場合は中断**し、作業ブランチを切るよう促す（`main` から直接 PR を作らない）。
2. `git status` が clean か確認。未コミットの変更があれば先に `/commit` するよう促す。
3. `gh auth status` で gh が認証済みか確認。

## 手順

1. **差分把握**（並列）:
   - `git log --oneline main..HEAD`（このブランチのコミット群）
   - `git diff main...HEAD --stat`（変更範囲）
2. **タイトル**: Conventional Commits 形式 `<type>(<scope>): <subject>`。
   - コミットが 1 つならそのメッセージを流用。複数なら全体を要約する 1 行を作る。
   - type/scope は commit.md と同じ語彙（`feat`/`fix`/`docs`/`build` … / `backend`/`frontend`/`db`/`docker`/`ci`）。
3. **本文**: なぜ（why）と変更概要を箇条書きで。**AI co-author / 自動生成 footer は付けない**（commit.md の方針）。
4. **push**: `git push -u origin HEAD`。
5. **作成**: HEREDOC で本文を渡して実行（`$ARGUMENTS` に `draft` 等があれば反映）:

   ```bash
   gh pr create --title "feat(scope): ..." --body "$(cat <<'EOF'
   ## 概要
   - ...

   ## 変更点
   - ...

   ## 確認
   - [ ] `/check all` が green
   EOF
   )"
   ```

6. 作成された PR の URL を報告する。

## 補足

- **コードレビューは作らない**: レビューは組み込みの `/code-review`（または `/review`）を使う。このコマンドは重複させない。
- 明示指示がない限り `--draft` は付けない。

引数: $ARGUMENTS
