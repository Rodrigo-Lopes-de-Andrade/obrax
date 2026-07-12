"""Engines e sessões SQLAlchemy compartilhados pela aplicação.

Três engines, cada um autenticado como um role Postgres diferente (ver
`alembic/versions/0001_extensions_and_roles.py`):

- `engine`/`SessionLocal`: DSN "crua" do `.env` (role `obrax` local, sem RLS
  forçada aplicável — usada por Alembic, scripts de seed e fixtures de teste
  que precisam bypassar RLS para montar cenários multi-tenant).
- `app_user_engine`/`AppUserSessionLocal`: role `app_user` (sujeito a RLS).
  É o que a API usa em toda request autenticada, via `app.core.deps.get_db`,
  que aplica `SET LOCAL app.company_id` antes de qualquer query.
- `app_admin_engine`/`AppAdminSessionLocal`: role `app_admin` (BYPASSRLS).
  Usado apenas nos poucos fluxos pré-tenant (login por email, aceitar
  convite) via `app.core.deps.get_admin_db` — ver docstring lá.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _is_pooler(url: str) -> bool:
    """Verdadeiro se a DSN aponta para um pooler externo (Supabase/pgbouncer)."""
    return ":6543" in url or "pgbouncer=true" in url or "pooler." in url


def _connect_args(url: str) -> dict[str, Any]:
    """Args de conexão psycopg por DSN.

    Atrás de um pooler em *transaction mode* (pgbouncer — ex.: Supabase na porta
    :6543 ou `?pgbouncer=true`), cada transação pode cair numa conexão de servidor
    diferente, então prepared statements server-side do psycopg3 quebram
    ("prepared statement does not exist"). `prepare_threshold=None` desliga a
    preparação automática. Numa conexão direta ou pooler *session mode* (:5432),
    onde a conexão é fixa por sessão, mantemos o default (mais rápido).
    """
    if ":6543" in url or "pgbouncer=true" in url:
        return {"prepare_threshold": None}
    return {}


def _engine_kwargs(url: str) -> dict[str, Any]:
    """kwargs de pool/conexão do engine por DSN.

    Atrás de um pooler externo (Supabase/pgbouncer) NÃO empilhamos um pool do
    SQLAlchemy por cima: `NullPool` abre/fecha a conexão por uso e deixa o pooler
    gerenciar — mantém o número de conexões concorrentes mínimo (evita esgotar o
    limite de clientes do pooler, que causava hangs sob carga de testes) e evita
    conexões ociosas que ficam stale no pooler. Em conexão direta/local, um
    QueuePool com `pool_pre_ping` é melhor (reaproveita conexões).
    """
    connect_args = _connect_args(url)
    if _is_pooler(url):
        return {"poolclass": NullPool, "connect_args": connect_args}
    return {"pool_pre_ping": True, "connect_args": connect_args}


engine = create_engine(settings.database_url, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app_user_engine = create_engine(
    settings.app_user_database_url, future=True, **_engine_kwargs(settings.app_user_database_url)
)
AppUserSessionLocal = sessionmaker(
    bind=app_user_engine, autoflush=False, autocommit=False, future=True
)

app_admin_engine = create_engine(
    settings.app_admin_database_url, future=True, **_engine_kwargs(settings.app_admin_database_url)
)
AppAdminSessionLocal = sessionmaker(
    bind=app_admin_engine, autoflush=False, autocommit=False, future=True
)


def get_session() -> Session:
    """Sessão avulsa (role `obrax`, sem RLS) para uso em scripts/seed."""
    return SessionLocal()
