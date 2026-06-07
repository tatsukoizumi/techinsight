# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Frontend: 公式 node:24-bookworm-slim + corepack 同梱の pnpm。
# build context はリポジトリルート。
#
# バージョンはホスト側の mise.toml / packageManager と一致させること:
#   - Node 24.16.0 ←→  mise.toml:        node = "24.16.0"
#   - pnpm 11.5.2  ←→  package.json:     "packageManager": "pnpm@11.5.2"
# ---------------------------------------------------------------------------
FROM node:24.16.0-bookworm-slim AS base

# ベースイメージ build 時から経過した分の OS セキュリティパッチを適用 (HIGH 解消)
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV COREPACK_ENABLE_AUTO_PIN=0 \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# corepack 有効化（root 権限で /usr/local/bin に書く）
RUN corepack enable

# /app を node ユーザ所有に。以降は node 同梱の非 root ユーザで作業する。
RUN mkdir -p /app && chown -R node:node /app
WORKDIR /app
USER node

# 依存マニフェストだけ先に COPY してレイヤキャッシュ
COPY --chown=node:node package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY --chown=node:node frontend/package.json ./frontend/
RUN pnpm install --frozen-lockfile

# アプリ本体
COPY --chown=node:node frontend/ ./frontend/

WORKDIR /app/frontend
EXPOSE 3000
# 開発サーバ。docker-compose.yml で app/ 等を bind mount して HMR を効かせる。
CMD ["pnpm", "dev"]
