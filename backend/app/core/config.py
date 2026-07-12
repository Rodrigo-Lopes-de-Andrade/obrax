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
    # Object store S3-compatível (Supabase Storage em staging/prod; MinIO local
    # em dev — ver docker-compose.yml). O mesmo cliente boto3 serve os dois via
    # `endpoint_url`. Defaults abaixo apontam pro MinIO local; sobrescreva por
    # env (secrets manager) em staging/prod.
    storage_endpoint_url: str
    storage_region: str
    storage_access_key: str
    storage_secret_key: str
    storage_bucket_documents: str
    # TTL das URLs de upload assinadas (docs/ESPEC.md § 7: presigned PUT 15 min).
    storage_presign_ttl: int
    # Realtime (B4.3): entrega de eventos do chat de tickets no canal Supabase.
    # Desligado por padrão (dev/CI usam o publisher no-op); ligue em staging/prod
    # com REALTIME_ENABLED=true + SUPABASE_URL + SUPABASE_SERVICE_KEY.
    realtime_enabled: bool
    supabase_url: str
    supabase_service_key: str
    # PDF do orçamento (B6.3). `pdf_renderer_url` vazio => renderer de dev
    # (devolve o próprio HTML como bytes, sem headless); em staging/prod aponta
    # pro sidecar Puppeteer/Chromium que converte HTML→PDF (ver
    # app/integrations/pdf.py). `pdf_download_ttl`: TTL (s) da URL assinada de
    # download do PDF — 1h, bem maior que o presign de upload por ser leitura.
    pdf_renderer_url: str
    pdf_download_ttl: int
    # Agentes IA (Módulo 3, Sprint 10). `uazap_webhook_secret` valida o HMAC do
    # webhook do Uazap (B10.1); vazio => o webhook rejeita toda requisição (fail
    # closed) exceto em testes que sobrescrevem a dependency. `uazap_base_url`
    # vazio => cliente Uazap no-op (dev/CI, não envia nada — ver integrations).
    uazap_webhook_secret: str
    uazap_base_url: str
    uazap_token: str


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
        storage_endpoint_url=os.environ.get("STORAGE_ENDPOINT_URL", "http://localhost:9000"),
        storage_region=os.environ.get("STORAGE_REGION", "us-east-1"),
        storage_access_key=os.environ.get("STORAGE_ACCESS_KEY", "obrax"),
        storage_secret_key=os.environ.get("STORAGE_SECRET_KEY", "obrax-dev-secret"),
        storage_bucket_documents=os.environ.get("STORAGE_BUCKET_DOCUMENTS", "documents-dev"),
        storage_presign_ttl=int(os.environ.get("STORAGE_PRESIGN_TTL", "900")),
        realtime_enabled=os.environ.get("REALTIME_ENABLED", "").lower() in ("1", "true", "yes"),
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        supabase_service_key=os.environ.get("SUPABASE_SERVICE_KEY", ""),
        pdf_renderer_url=os.environ.get("PDF_RENDERER_URL", ""),
        pdf_download_ttl=int(os.environ.get("PDF_DOWNLOAD_TTL", "3600")),
        uazap_webhook_secret=os.environ.get("UAZAP_WEBHOOK_SECRET", ""),
        uazap_base_url=os.environ.get("UAZAP_BASE_URL", ""),
        uazap_token=os.environ.get("UAZAP_TOKEN", ""),
    )


settings = get_settings()
