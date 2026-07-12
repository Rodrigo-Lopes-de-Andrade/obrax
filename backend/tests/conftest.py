from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app


def _dsn_with_role(role: str, password: str) -> str:
    """Reconstrói a DSN de `DATABASE_URL` trocando usuário/senha pelo role
    de aplicação informado, mantendo host/porta/database originais.

    Preserva o sufixo `.<project_ref>` do pooler do Supabase (Supavisor autentica
    como `<role>.<project_ref>`); numa conexão direta/local usa o role puro.
    """
    parts = urlsplit(settings.database_url_raw)
    original_user = parts.username or ""
    tenant = original_user.split(".", 1)[1] if "." in original_user else None
    user = f"{role}.{tenant}" if tenant else role
    netloc = f"{user}:{password}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


APP_USER_DSN = _dsn_with_role("app_user", "app_user_dev_only")


@pytest.fixture
def two_tenants() -> Iterator[dict[str, dict[str, str]]]:
    """Cria 2 empresas + 1 usuário (owner) cada, via role `obrax` (bypassa
    RLS), e remove tudo ao final do teste.
    """
    fixtures = [
        ("A", "33333333000191", "isolamento-a@example.com"),
        ("B", "44444444000191", "isolamento-b@example.com"),
    ]
    cnpjs = [c for _, c, _ in fixtures]
    emails = [e for _, _, e in fixtures]
    with SessionLocal() as session:
        # Auto-cura: remove órfãos destes CNPJs/emails fixos deixados por uma run
        # anterior que abortou antes do teardown (ex.: timeout). Torna a fixture
        # repetível mesmo após crash, sem depender de limpeza externa.
        session.execute(text("DELETE FROM companies WHERE cnpj = ANY(:c)"), {"c": cnpjs})
        session.execute(text("DELETE FROM users WHERE email = ANY(:e)"), {"e": emails})
        session.commit()

        tenants: dict[str, dict[str, str]] = {}
        for label, cnpj, email in fixtures:
            company_id = session.execute(
                text(
                    "INSERT INTO companies (cnpj, razao_social) VALUES (:cnpj, :razao) RETURNING id"
                ),
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


@dataclass(frozen=True)
class SeededUser:
    """Empresa + usuário (com senha real) + vínculo/role, semeados para testes
    de API. `access_token`/`auth_header` mintam um JWT de acesso válido para
    esse tenant — a `TenantMiddleware` popula o contexto a partir dele."""

    company_id: str
    user_id: str
    email: str
    password: str
    role: str

    @property
    def access_token(self) -> str:
        return create_access_token(
            user_id=uuid.UUID(self.user_id),
            company_id=uuid.UUID(self.company_id),
            role=self.role,
        ).token

    @property
    def auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP de teste contra a app FastAPI real (cookie jar por teste)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed_tenant() -> Iterator[Callable[..., SeededUser]]:
    """Fábrica de tenants: cria empresa + usuário (senha Argon2id real) +
    vínculo, via role `obrax` (bypassa RLS). Remove tudo ao final (o DELETE em
    `companies` cascateia para `user_company_role`/`invitations`)."""
    company_ids: list[str] = []
    user_ids: list[str] = []

    def _create(
        *,
        role: str = "owner",
        password: str = "senha-de-teste-123",
        email: str | None = None,
    ) -> SeededUser:
        email = email or f"user-{secrets.token_hex(6)}@example.com"
        cnpj = "".join(secrets.choice("0123456789") for _ in range(14))
        with SessionLocal() as session:
            company_id = session.execute(
                text(
                    "INSERT INTO companies (cnpj, razao_social) VALUES (:cnpj, :razao) RETURNING id"
                ),
                {"cnpj": cnpj, "razao": "Tenant Teste Ltda"},
            ).scalar_one()
            user_id = session.execute(
                text(
                    "INSERT INTO users (email, password_hash, nome) "
                    "VALUES (:email, :password_hash, :nome) RETURNING id"
                ),
                {"email": email, "password_hash": hash_password(password), "nome": "Teste"},
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO user_company_role (company_id, user_id, role) "
                    "VALUES (:cid, :uid, CAST(:role AS user_role))"
                ),
                {"cid": company_id, "uid": user_id, "role": role},
            )
            session.commit()
        company_ids.append(str(company_id))
        user_ids.append(str(user_id))
        return SeededUser(
            company_id=str(company_id),
            user_id=str(user_id),
            email=email,
            password=password,
            role=role,
        )

    yield _create

    with SessionLocal() as session:
        for cid in company_ids:
            session.execute(text("DELETE FROM companies WHERE id = :id"), {"id": cid})
        for uid in user_ids:
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        session.commit()
