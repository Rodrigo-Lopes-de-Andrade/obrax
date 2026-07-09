"""B4.2 — CRUD de tickets (US-08). Contrato em docs/ESPEC.md § 6."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


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


def _create_ticket(client: TestClient, owner: SeededUser, obra_id: str, **over: object) -> dict:
    body: dict = {"titulo": "Vazamento no 3º andar"}
    body.update(over)
    resp = client.post(f"/api/v1/obras/{obra_id}/tickets", headers=owner.auth_header, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_ticket_defaults(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    t = _create_ticket(client, owner, obra_id, descricao="Infiltração na laje.")
    assert uuid.UUID(t["id"])
    assert t["obra_id"] == obra_id
    assert t["status"] == "aberto"
    assert t["created_by"] == owner.user_id
    assert t["descricao"] == "Infiltração na laje."


def test_create_titulo_vazio_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets", headers=owner.auth_header, json={"titulo": ""}
    )
    assert resp.status_code == 422


def test_create_descricao_grande_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": "X", "descricao": "a" * 5001},
    )
    assert resp.status_code == 422


def test_create_obra_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        f"/api/v1/obras/{uuid.uuid4()}/tickets",
        headers=owner.auth_header,
        json={"titulo": "X"},
    )
    assert resp.status_code == 422


def test_list_filtra_por_obra_e_status(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra1 = _seed_obra(client, owner)
    # segunda obra no mesmo tenant (cliente PF com CPF válido — há CHECK no banco)
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PF", "documento": "52998224725", "nome": "Cliente 2"},
    )
    assert resp.status_code == 201, resp.text
    obra2 = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-2", "nome": "Obra 2"},
    ).json()["id"]

    t1 = _create_ticket(client, owner, obra1)
    _create_ticket(client, owner, obra2)
    # resolve t1
    client.patch(
        f"/api/v1/tickets/{t1['id']}/status",
        headers=owner.auth_header,
        json={"status": "resolvido"},
    )

    por_obra = client.get(f"/api/v1/tickets?obra_id={obra1}", headers=owner.auth_header).json()
    assert [x["id"] for x in por_obra["items"]] == [t1["id"]]

    resolvidos = client.get("/api/v1/tickets?status=resolvido", headers=owner.auth_header).json()
    assert [x["id"] for x in resolvidos["items"]] == [t1["id"]]


def test_patch_status(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    t = _create_ticket(client, owner, obra_id)
    resp = client.patch(
        f"/api/v1/tickets/{t['id']}/status",
        headers=owner.auth_header,
        json={"status": "andamento"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "andamento"


def test_patch_status_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    t = _create_ticket(client, owner, obra_id)
    resp = client.patch(
        f"/api/v1/tickets/{t['id']}/status",
        headers=owner.auth_header,
        json={"status": "cancelado"},
    )
    assert resp.status_code == 422


def test_get_e_delete_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    t = _create_ticket(client, owner, obra_id)

    assert client.delete(f"/api/v1/tickets/{t['id']}", headers=owner.auth_header).status_code == 204
    assert client.get(f"/api/v1/tickets/{t['id']}", headers=owner.auth_header).status_code == 404
    assert client.delete(f"/api/v1/tickets/{t['id']}", headers=owner.auth_header).status_code == 404
    assert client.get("/api/v1/tickets", headers=owner.auth_header).json()["items"] == []


def test_write_roles_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    t = _create_ticket(client, owner, obra_id)
    viewer = seed_tenant(role="viewer")

    assert (
        client.patch(
            f"/api/v1/tickets/{t['id']}/status",
            headers=viewer.auth_header,
            json={"status": "fechado"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/tickets/{t['id']}", headers=viewer.auth_header).status_code == 403
    )


def test_cross_tenant_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    t_b = _create_ticket(client, owner_b, obra_b)

    assert (
        client.get(f"/api/v1/tickets/{t_b['id']}", headers=owner_a.auth_header).status_code == 404
    )
    assert (
        client.patch(
            f"/api/v1/tickets/{t_b['id']}/status",
            headers=owner_a.auth_header,
            json={"status": "fechado"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/tickets", headers=owner_a.auth_header).json()["items"] == []
