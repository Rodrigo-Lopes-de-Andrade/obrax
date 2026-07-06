"""Engine e sessão SQLAlchemy compartilhados pela aplicação."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Session:
    """Cria uma nova sessão. O Estágio B (FastAPI) deve envolver isso em uma
    dependency que aplica `SET LOCAL app.company_id` (TenantMiddleware) antes
    de qualquer query — ver docs/ESPEC.md seção 3.
    """
    return SessionLocal()
