"""B1.4 — magic links single-use (docs/SPRINTS.md, critério de aceite:
"Link valida 1x, expira, tentativa de reuse falha 401").
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.security import create_magic_link_token
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


def _magic_token_for(user: SeededUser) -> str:
    return create_magic_link_token(
        user_id=uuid.UUID(user.user_id),
        company_id=uuid.UUID(user.company_id),
        purpose="login",
    ).token


def test_consumo_valido_retorna_tokens(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant()
    resp = client.post("/api/v1/auth/magic/consume", json={"token": _magic_token_for(user)})

    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert "refresh_token=" in resp.headers.get("set-cookie", "")


def test_reuse_do_mesmo_token_falha_401(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant()
    token = _magic_token_for(user)

    assert client.post("/api/v1/auth/magic/consume", json={"token": token}).status_code == 200
    # Segundo consumo do mesmo jti → 401 (registrado em consumed_tokens).
    resp = client.post("/api/v1/auth/magic/consume", json={"token": token})
    assert resp.status_code == 401


def test_token_expirado_falha_401(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": user.user_id,
            "company_id": user.company_id,
            "purpose": "login",
            "type": "magic",
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "jti": str(uuid.uuid4()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    resp = client.post("/api/v1/auth/magic/consume", json={"token": expired})
    assert resp.status_code == 401


def test_token_de_tipo_errado_falha_401(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant()
    # Um token de acesso (type=access) não pode ser consumido como magic link.
    resp = client.post("/api/v1/auth/magic/consume", json={"token": user.access_token})
    assert resp.status_code == 401
