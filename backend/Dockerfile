# syntax=docker/dockerfile:1
# Backend Obrax — FastAPI servido por gunicorn + workers uvicorn (ver RUNBOOK §3).
# Build context = backend/.  Imagem multi-stage: builder resolve as deps com uv,
# runtime carrega só o venv + código.

# ---- builder: resolve as dependências num venv isolado, com uv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Camada cacheável: só o manifesto + lock, sem o código. Inclui o extra
# `observability` (OpenTelemetry) — prod exporta traces/logs via OTLP (B11.2).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --extra observability

# Agora o código + instala o próprio projeto no venv.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra observability

# ---- runtime: imagem enxuta só com o venv + app ----
FROM python:3.12-slim-bookworm AS runtime

# Usuário não-root.
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080
USER app
EXPOSE 8080

# WEB_CONCURRENCY ajusta o nº de workers. O logging estruturado (JSON) é ligado
# pela app com LOG_FORMAT=json (B11.1); gunicorn manda o resto para stdout/stderr.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --graceful-timeout 30"]
