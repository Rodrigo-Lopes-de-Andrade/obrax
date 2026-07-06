"""Configuração central do backend.

Fonte da verdade das variáveis de ambiente é o `.env` na raiz do monorepo
(ver `docs/CLAUDE.md` > Setup e Execução). Este módulo é importado tanto
pela aplicação quanto pelo `alembic/env.py`, para nunca duplicar a lógica
de leitura de `DATABASE_URL`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]  # backend/app
BACKEND_DIR = APP_DIR.parent  # backend/
REPO_ROOT = BACKEND_DIR.parent  # raiz do monorepo

# Carrega o .env da raiz do monorepo (não sobrescreve variáveis já setadas
# no ambiente, ex.: exportadas manualmente ou injetadas via CI/Docker).
load_dotenv(REPO_ROOT / ".env", override=False)

# Credenciais de dev dos roles de aplicação, criadas em
# `alembic/versions/0001_extensions_and_roles.py`. Mesmo padrão já usado em
# `tests/conftest.py` (`_dsn_with_role`) — em staging/prod, defina
# `APP_USER_DATABASE_URL`/`APP_ADMIN_DATABASE_URL` explicitamente no `.env`
# (secrets manager) para sobrescrever este fallback local.
_APP_USER_DEV_PASSWORD = "app_user_dev_only"
_APP_ADMIN_DEV_PASSWORD = "app_admin_dev_only"


@dataclass(frozen=True)
class Settings:
    # URL "crua" tal como definida no `.env` (driver-agnostic), útil para
    # conectar via psycopg puro (ex.: testes de RLS que trocam de role).
    database_url_raw: str
    # URL normalizada para o dialeto `postgresql+psycopg` (psycopg 3), que é
    # o driver usado pelo SQLAlchemy neste projeto (ver docs/CLAUDE.md).
    database_url: str
    # DSN de runtime da API — conecta como `app_user` (sujeito a RLS). Usada
    # pela TenantMiddleware/`get_db` a cada request (ver docs/ESPEC.md § 3).
    app_user_database_url: str
    # DSN administrativa — conecta como `app_admin` (BYPASSRLS). Usada apenas
    # nos poucos fluxos que precisam operar antes de um tenant ser conhecido
    # (login por email, aceitar convite) — ver app/core/deps.py.
    app_admin_database_url: str
    jwt_secret: str
    # "development" desliga o atributo `Secure` do cookie de refresh (permite
    # testar via curl/http local); qualquer outro valor liga `Secure`.
    environment: str


def _to_psycopg_dsn(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _dsn_with_role(url: str, role: str, password: str) -> str:
    """Reconstrói `url` trocando usuário/senha pelo role informado, mantendo
    host/porta/database originais (mesma lógica de `tests/conftest.py`)."""
    parts = urlsplit(url)
    netloc = f"{role}:{password}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@lru_cache
def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL não definida. Configure no `.env` da raiz do monorepo "
            "(ver docs/CLAUDE.md)."
        )
    jwt_secret = os.environ.get("JWT_SECRET")
    if not jwt_secret or jwt_secret == "change-me":
        raise RuntimeError(
            "JWT_SECRET não definida (ou ainda no placeholder `change-me`). "
            "Configure no `.env` da raiz do monorepo (ver docs/CLAUDE.md)."
        )

    app_user_dsn = os.environ.get("APP_USER_DATABASE_URL") or _dsn_with_role(
        database_url, "app_user", _APP_USER_DEV_PASSWORD
    )
    app_admin_dsn = os.environ.get("APP_ADMIN_DATABASE_URL") or _dsn_with_role(
        database_url, "app_admin", _APP_ADMIN_DEV_PASSWORD
    )

    return Settings(
        database_url_raw=database_url,
        database_url=_to_psycopg_dsn(database_url),
        app_user_database_url=_to_psycopg_dsn(app_user_dsn),
        app_admin_database_url=_to_psycopg_dsn(app_admin_dsn),
        jwt_secret=jwt_secret,
        environment=os.environ.get("ENVIRONMENT", "development"),
    )


settings = get_settings()
