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

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app_user_engine = create_engine(settings.app_user_database_url, pool_pre_ping=True, future=True)
AppUserSessionLocal = sessionmaker(
    bind=app_user_engine, autoflush=False, autocommit=False, future=True
)

app_admin_engine = create_engine(settings.app_admin_database_url, pool_pre_ping=True, future=True)
AppAdminSessionLocal = sessionmaker(
    bind=app_admin_engine, autoflush=False, autocommit=False, future=True
)


def get_session() -> Session:
    """Sessão avulsa (role `obrax`, sem RLS) para uso em scripts/seed."""
    return SessionLocal()
