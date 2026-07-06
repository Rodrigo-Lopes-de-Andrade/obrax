from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal


def _dsn_with_role(role: str, password: str) -> str:
    """Reconstrói a DSN de `DATABASE_URL` trocando usuário/senha pelo role
    de aplicação informado, mantendo host/porta/database originais.
    """
    parts = urlsplit(settings.database_url_raw)
    netloc = f"{role}:{password}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


APP_USER_DSN = _dsn_with_role("app_user", "app_user_dev_only")


@pytest.fixture
def two_tenants() -> Iterator[dict[str, dict[str, str]]]:
    """Cria 2 empresas + 1 usuário (owner) cada, via role `obrax` (bypassa
    RLS), e remove tudo ao final do teste.
    """
    with SessionLocal() as session:
        tenants: dict[str, dict[str, str]] = {}
        for label, cnpj, email in [
            ("A", "33333333000191", "isolamento-a@example.com"),
            ("B", "44444444000191", "isolamento-b@example.com"),
        ]:
            company_id = session.execute(
                text("INSERT INTO companies (cnpj, razao_social) VALUES (:cnpj, :razao) RETURNING id"),
                {"cnpj": cnpj, "razao": f"Tenant {label} Ltda"},
            ).scalar_one()
            user_id = session.execute(
                text(
                    "INSERT INTO users (email, password_hash, nome) "
                    "VALUES (:email, 'x', :nome) RETURNING id"
                ),
                {"email": email, "nome": f"User {label}"},
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO user_company_role (company_id, user_id, role) "
                    "VALUES (:company_id, :user_id, 'owner')"
                ),
                {"company_id": company_id, "user_id": user_id},
            )
            tenants[label] = {"company_id": str(company_id), "user_id": str(user_id)}
        session.commit()

    yield tenants

    with SessionLocal() as session:
        for t in tenants.values():
            session.execute(text("DELETE FROM companies WHERE id = :id"), {"id": t["company_id"]})
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": t["user_id"]})
        session.commit()


@pytest.fixture
def app_user_conn() -> Iterator[psycopg.Connection]:
    """Conexão autenticada como `app_user` (role de runtime, sujeita a RLS —
    sem BYPASSRLS)."""
    conn = psycopg.connect(APP_USER_DSN, autocommit=False)
    yield conn
    conn.close()
