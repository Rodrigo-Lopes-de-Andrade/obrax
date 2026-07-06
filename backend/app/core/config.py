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

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]  # backend/app
BACKEND_DIR = APP_DIR.parent  # backend/
REPO_ROOT = BACKEND_DIR.parent  # raiz do monorepo

# Carrega o .env da raiz do monorepo (não sobrescreve variáveis já setadas
# no ambiente, ex.: exportadas manualmente ou injetadas via CI/Docker).
load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    # URL "crua" tal como definida no `.env` (driver-agnostic), útil para
    # conectar via psycopg puro (ex.: testes de RLS que trocam de role).
    database_url_raw: str
    # URL normalizada para o dialeto `postgresql+psycopg` (psycopg 3), que é
    # o driver usado pelo SQLAlchemy neste projeto (ver docs/CLAUDE.md).
    database_url: str


def _to_psycopg_dsn(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@lru_cache
def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL não definida. Configure no `.env` da raiz do monorepo "
            "(ver docs/CLAUDE.md)."
        )
    return Settings(database_url_raw=database_url, database_url=_to_psycopg_dsn(database_url))


settings = get_settings()
