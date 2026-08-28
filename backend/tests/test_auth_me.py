"""`GET /api/v1/auth/me` — perfil da sessão (nome/e-mail do banco, role do JWT).

Endpoint que a Topbar consome para deixar de exibir usuário fixo. Roda sob
`get_db` (RLS): a policy `users_tenant_select` restringe ao tenant do token.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from starlette.testclient import TestClient

from app.core.security import create_access_token
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


def test_me_retorna_perfil_da_sessao(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant(role="gestor")

    resp = client.get("/api/v1/auth/me", headers=user.auth_header)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "id": user.user_id,
        "nome": "Teste",
        "email": user.email,
        "role": "gestor",
    }


def test_me_sem_token_401(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_usuario_inexistente_401(client: TestClient, seed_tenant: SeedTenant) -> None:
    """JWT bem assinado cujo `sub` não existe mais (usuário removido): a RLS não
    devolve linha e o endpoint recusa a sessão em vez de responder com dados vazios."""
    owner = seed_tenant(role="owner")
    token = create_access_token(
        user_id=uuid.uuid4(),
        company_id=uuid.UUID(owner.company_id),
        role="owner",
    ).token

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
