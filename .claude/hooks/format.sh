#!/usr/bin/env bash
#
# PostToolUse hook: auto-format + lint the single file Claude just edited.
#
# Routing by path/extension:
#   frontend/*.{ts,tsx,js,jsx,mjs,cjs,json,jsonc} -> Biome (format + lint fix + import sort)
#   backend/*.py                                  -> Ruff (format + lint fix)
#   root *.{md,yaml,yml,json}  (outside frontend) -> Prettier (format)
#
# Behaviour: silently auto-fix and exit 0. If unfixable lint issues remain,
# print them to stderr and exit 2 so Claude self-corrects.
set -euo pipefail

payload="$(cat)"

# Extract the edited file path (jq preferred, python3 fallback).
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
else
  file="$(printf '%s' "$payload" | python3 -c \
    'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' \
    2>/dev/null || true)"
fi

# Nothing to do for missing / deleted files.
[ -n "$file" ] || exit 0
[ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Only act on files inside this project.
case "$file" in
  "$root"/*) ;;
  *) exit 0 ;;
esac

fail() {
  printf 'format.sh: unresolved issues in %s\n\n%s\n' "$file" "$1" >&2
  exit 2
}

case "$file" in
  "$root"/frontend/*.ts | "$root"/frontend/*.tsx | "$root"/frontend/*.js | \
  "$root"/frontend/*.jsx | "$root"/frontend/*.mjs | "$root"/frontend/*.cjs | \
  "$root"/frontend/*.json | "$root"/frontend/*.jsonc)
    cd "$root"
    out="$(pnpm --filter frontend exec biome check --write "$file" 2>&1)" || fail "$out"
    ;;

  "$root"/backend/*.py)
    cd "$root/backend"
    uv run ruff format "$file" >/dev/null 2>&1 || true
    out="$(uv run ruff check --fix "$file" 2>&1)" || fail "$out"
    ;;

  "$root"/frontend/*)
    # Other frontend files are Biome's domain but not formatted per-file; skip.
    exit 0
    ;;

  *.md | *.markdown | *.yaml | *.yml | *.json)
    cd "$root"
    out="$(pnpm exec prettier --write "$file" 2>&1)" || fail "$out"
    ;;

  *)
    exit 0
    ;;
esac

exit 0
