# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Backend: 公式 python:3.14-slim + Astral 公式イメージから uv バイナリだけ COPY。
# build context はリポジトリルート。
#
# バージョンはホスト側の mise.toml と一致させること:
#   - Python 3.14.5  ←→  mise.toml: python = "3.14.5"
#   - uv     0.11.19 ←→  mise.toml: uv     = "0.11.19"
# ---------------------------------------------------------------------------
FROM python:3.14.5-slim AS base

# ベースイメージ build 時から経過した分の OS セキュリティパッチを適用 (HIGH 解消)
# その後 apt キャッシュを完全削除してイメージサイズを抑える。
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# uv バイナリのみ取り込み（Astral 公式イメージから）
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /usr/local/bin/

# 非 root ユーザ（UID 1000）。HOME を作って uv のキャッシュが書ける場所を確保。
RUN useradd --create-home --uid 1000 --shell /bin/bash app \
    && mkdir -p /app/backend \
    && chown -R app:app /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app/backend
USER app

# 依存だけ先に install してレイヤキャッシュを効かせる
COPY --chown=app:app backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --frozen --no-install-project

# アプリ本体
COPY --chown=app:app backend/ /app/backend/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
