"""B1.2 — isolamento multi-tenant ponta a ponta (docs/SPRINTS.md, critério de
aceite: "teste isolamento passa (tenant A ≠ B)").

Diferente de `test_rls_isolation.py` (que valida a RLS direto no Postgres via
`app_user`), aqui o caminho completo é exercido: JWT → `TenantMiddleware` →
`get_db` (`SET LOCAL app.company_id`) → RLS. Cada owner só enxerga os convites
da própria empresa via `GET /api/v1/users/invite`.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


def _invite(client: TestClient, owner: SeededUser, email: str) -> None:
    resp = client.post(
        "/api/v1/users/invite",
        headers=owner.auth_header,
        json={"email": email, "role": "gestor"},
    )
    assert resp.status_code == 201


def _invited_emails(client: TestClient, owner: SeededUser) -> set[str]:
    resp = client.get("/api/v1/users/invite", headers=owner.auth_header)
    assert resp.status_code == 200
    return {item["email"] for item in resp.json()}


def test_owner_so_ve_convites_da_propria_empresa(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")

    _invite(client, owner_a, "convite-a@example.com")
    _invite(client, owner_b, "convite-b@example.com")

    emails_a = _invited_emails(client, owner_a)
    emails_b = _invited_emails(client, owner_b)

    assert "convite-a@example.com" in emails_a
    assert "convite-b@example.com" not in emails_a

    assert "convite-b@example.com" in emails_b
    assert "convite-a@example.com" not in emails_b
