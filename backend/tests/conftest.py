from __future__ import annotations

import os
from urllib.parse import urlsplit

import pytest

# Guarda anti-prod — DEVE rodar antes de importar `app.core.config`, que faz
# `load_dotenv(REPO_ROOT/.env, override=False)` no import. O `.env` da raiz tem
# credenciais de PRODUÇÃO e `override=False` significa: toda chave que NÃO está em
# `os.environ` é preenchida a partir dele. Logo, a defesa é dupla:
#
# 1. `DATABASE_URL` precisa vir explícito do ambiente (os testes mutam o banco);
#    sem ele aborta a sessão em vez de cair no fallback de produção.
# 2. Toda chave de integração é fixada aqui com `setdefault` nos valores locais/CI
#    (MinIO do docker-compose, integrações vazias). `setdefault` é deliberado: quem
#    exporta um valor no shell o mantém, mas nada mais vem do `.env`. Assim os
#    testes nunca falam com o storage/Supabase/UAZAPI de produção nem com serviços
#    pagos (Anthropic, OpenAI, Sentry, PostHog).
# 3. Mesmo com o DSN explícito, se o host do `DATABASE_URL` não for local, recusa
#    (um DSN remoto colado do `.env` é o acidente que isto evita), a menos que
#    `OBRAX_TESTS_ALLOW_REMOTE_DB=1`.
if not os.environ.get("DATABASE_URL"):
    raise pytest.UsageError(
        "DATABASE_URL não está setado no ambiente. Os testes mutam o banco e o "
        "fallback do .env aponta para PROD — recuso rodar. Rode com um DATABASE_URL "
        "explícito de local/staging, ex.:\n"
        '  DATABASE_URL="postgresql://.../postgres" pytest'
    )

_LOCAL_TEST_ENV = {
    # Storage: MinIO do docker-compose (mesmos defaults de config.py / CI).
    "STORAGE_ENDPOINT_URL": "http://localhost:9000",
    "STORAGE_REGION": "us-east-1",
    "STORAGE_ACCESS_KEY": "obrax",
    "STORAGE_SECRET_KEY": "obrax-dev-secret",
    "STORAGE_BUCKET_DOCUMENTS": "documents-dev",
    "STORAGE_PRESIGN_TTL": "900",
    # Integrações externas: vazias = desabilitadas.
    "SUPABASE_URL": "",
    "SUPABASE_SERVICE_KEY": "",
    "SUPABASE_SECRET_KEY": "",
    "SUPABASE_PUBLISHABLE_KEY": "",
    "SUPABASE_JWKS_URL": "",
    "UAZAPI_BASE_URL": "",
    "UAZAPI_TOKEN": "",
    "UAZAPI_WEBHOOK_SECRET": "",
    "REALTIME_ENABLED": "",
    "PDF_RENDERER_URL": "",
    # Vazio → config deriva as DSNs de app a partir do DATABASE_URL explícito.
    "APP_USER_DATABASE_URL": "",
    "APP_ADMIN_DATABASE_URL": "",
    # Serviços pagos/observabilidade: nunca chamar a partir dos testes.
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "SENTRY_DSN": "",
    "POSTHOG_API_KEY": "",
}
for _key, _value in _LOCAL_TEST_ENV.items():
    os.environ.setdefault(_key, _value)

_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}
_db_host = (urlsplit(os.environ["DATABASE_URL"]).hostname or "").lower()
if _db_host not in _LOCAL_DB_HOSTS and os.environ.get("OBRAX_TESTS_ALLOW_REMOTE_DB") != "1":
    raise pytest.UsageError(
        f"DATABASE_URL aponta para um host remoto ({_db_host or 'desconhecido'}). Os "
        "testes mutam o banco — recuso rodar contra algo que não seja local. Use o "
        "banco do docker compose (postgresql://obrax:obrax@localhost:5432/obrax) ou, "
        "se for um staging descartável, exporte OBRAX_TESTS_ALLOW_REMOTE_DB=1."
    )

import secrets  # noqa: E402
import uuid  # noqa: E402
from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from urllib.parse import urlunsplit  # noqa: E402

import psycopg  # noqa: E402
from sqlalchemy import text  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402


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
