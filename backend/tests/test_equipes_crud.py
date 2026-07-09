"""B3.6 — CRUD de equipe: add/list/remove membro de uma obra (US-07).
Contrato em docs/ESPEC.md § 6.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]
# (user_id, nome, email) de um usuário semeado num tenant.
MakeUser = Callable[..., tuple[str, str, str]]

CNPJ_VALIDO = "11222333000181"


@pytest.fixture
def seed_user() -> Iterator[MakeUser]:
    """Cria um usuário + vínculo (`user_company_role`) numa empresa, via `obrax`
    (bypassa RLS). Remove no teardown — o DELETE do user cascateia
    user_company_role/obra_membro (FK user_id CASCADE)."""
    created: list[str] = []

    def _make(
        company_id: str, *, nome: str = "Fulano de Tal", role: str = "campo"
    ) -> tuple[str, str, str]:
        email = f"membro-{uuid.uuid4().hex[:8]}@example.com"
        with SessionLocal() as session:
            uid = session.execute(
                text(
                    "INSERT INTO users (email, password_hash, nome) "
                    "VALUES (:email, 'x', :nome) RETURNING id"
                ),
                {"email": email, "nome": nome},
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO user_company_role (company_id, user_id, role) "
                    "VALUES (:cid, :uid, CAST(:role AS user_role))"
                ),
                {"cid": company_id, "uid": uid, "role": role},
            )
            session.commit()
        created.append(str(uid))
        return str(uid), nome, email

    yield _make

    with SessionLocal() as session:
        for uid in created:
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        session.commit()


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    )
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-1", "nome": "Reforma"},
    )
    return str(resp.json()["id"])


def test_add_e_list_membro(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    uid, nome, email = seed_user(owner.company_id, nome="Zé Eletricista")

    resp = client.post(
        f"/api/v1/obras/{obra_id}/membros",
        headers=owner.auth_header,
        json={"user_id": uid, "papel": "eletricista"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == uid
    assert body["nome"] == nome
    assert body["email"] == email
    assert body["papel"] == "eletricista"

    resp = client.get(f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [m["user_id"] for m in items] == [uid]


def test_add_duplicado_409(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    uid, _, _ = seed_user(owner.company_id)
    payload = {"user_id": uid, "papel": "mestre"}

    assert (
        client.post(
            f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header, json=payload
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header, json=payload
        ).status_code
        == 409
    )


def test_remove_e_readiciona(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    uid, _, _ = seed_user(owner.company_id)
    payload = {"user_id": uid, "papel": "pintor"}

    client.post(f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header, json=payload)
    assert (
        client.delete(
            f"/api/v1/obras/{obra_id}/membros/{uid}", headers=owner.auth_header
        ).status_code
        == 204
    )
    # Some da lista após remoção…
    resp = client.get(f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header)
    assert resp.json()["items"] == []
    # …e o UNIQUE parcial permite re-adicionar.
    assert (
        client.post(
            f"/api/v1/obras/{obra_id}/membros", headers=owner.auth_header, json=payload
        ).status_code
        == 201
    )


def test_add_user_fora_do_tenant_422(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_a = _seed_obra(client, owner_a)
    uid_b, _, _ = seed_user(owner_b.company_id)  # usuário do tenant B

    resp = client.post(
        f"/api/v1/obras/{obra_a}/membros",
        headers=owner_a.auth_header,
        json={"user_id": uid_b, "papel": "mestre"},
    )
    assert resp.status_code == 422


def test_remove_nao_membro_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.delete(
        f"/api/v1/obras/{obra_id}/membros/{uuid.uuid4()}", headers=owner.auth_header
    )
    assert resp.status_code == 404


def test_write_roles_403(client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    uid, _, _ = seed_user(owner.company_id)
    viewer = seed_tenant(role="viewer")

    assert (
        client.post(
            f"/api/v1/obras/{obra_id}/membros",
            headers=viewer.auth_header,
            json={"user_id": uid, "papel": "mestre"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/obras/{obra_id}/membros/{uid}", headers=viewer.auth_header
        ).status_code
        == 403
    )


def test_list_obra_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.get(f"/api/v1/obras/{uuid.uuid4()}/membros", headers=owner.auth_header)
    assert resp.status_code == 404


def test_cross_tenant_list_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    resp = client.get(f"/api/v1/obras/{obra_b}/membros", headers=owner_a.auth_header)
    assert resp.status_code == 404
