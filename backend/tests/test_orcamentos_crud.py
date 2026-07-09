"""B5.3 — CRUD de orçamento (US-11). Contrato em docs/ESPEC.md § 6/7."""

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


def _create_orcamento(client: TestClient, owner: SeededUser, obra_id: str, **over: object) -> dict:
    body: dict = {"titulo": "Orçamento Estrutural"}
    body.update(over)
    resp = client.post(f"/api/v1/obras/{obra_id}/orcamentos", headers=owner.auth_header, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_cria_versao_inicial(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)
    assert uuid.UUID(o["id"])
    assert o["obra_id"] == obra_id
    assert o["status"] == "rascunho"
    assert o["versao_atual"] == 1
    # versão 1 linkada e zerada
    assert o["versao"]["numero"] == 1
    assert o["versao"]["is_locked"] is False
    assert o["versao"]["preco_venda"] == "0.00"
    assert o["versao"]["markup_global"] == "0.0000"


def test_create_titulo_vazio_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/orcamentos", headers=owner.auth_header, json={"titulo": ""}
    )
    assert resp.status_code == 422


def test_create_obra_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        f"/api/v1/obras/{uuid.uuid4()}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "X"},
    )
    assert resp.status_code == 422


def test_list_filtra_por_obra(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra1 = _seed_obra(client, owner)
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PF", "documento": "52998224725", "nome": "Cliente 2"},
    )
    obra2 = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-2", "nome": "Obra 2"},
    ).json()["id"]

    o1 = _create_orcamento(client, owner, obra1)
    _create_orcamento(client, owner, obra2)

    por_obra = client.get(f"/api/v1/orcamentos?obra_id={obra1}", headers=owner.auth_header).json()
    assert [x["id"] for x in por_obra["items"]] == [o1["id"]]


def test_get_detail(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)
    got = client.get(f"/api/v1/orcamentos/{o['id']}", headers=owner.auth_header)
    assert got.status_code == 200
    assert got.json()["versao"]["numero"] == 1


def test_status_transicao_valida_e_aprovar_trava_versao(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)

    def patch(s: str) -> int:
        return client.patch(
            f"/api/v1/orcamentos/{o['id']}/status", headers=owner.auth_header, json={"status": s}
        ).status_code

    assert patch("aguardando_aprovacao") == 200
    resp = client.patch(
        f"/api/v1/orcamentos/{o['id']}/status",
        headers=owner.auth_header,
        json={"status": "aprovado"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "aprovado"
    assert resp.json()["versao"]["is_locked"] is True


def test_status_transicao_invalida_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)
    # rascunho → aprovado direto não é permitido
    resp = client.patch(
        f"/api/v1/orcamentos/{o['id']}/status",
        headers=owner.auth_header,
        json={"status": "aprovado"},
    )
    assert resp.status_code == 409


def test_status_enum_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)
    resp = client.patch(
        f"/api/v1/orcamentos/{o['id']}/status",
        headers=owner.auth_header,
        json={"status": "publicado"},
    )
    assert resp.status_code == 422


def test_delete_e_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    o = _create_orcamento(client, owner, obra_id)
    assert (
        client.delete(f"/api/v1/orcamentos/{o['id']}", headers=owner.auth_header).status_code == 204
    )
    assert client.get(f"/api/v1/orcamentos/{o['id']}", headers=owner.auth_header).status_code == 404
    assert client.get("/api/v1/orcamentos", headers=owner.auth_header).json()["items"] == []


def test_write_roles_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    viewer = seed_tenant(role="viewer")
    resp = client.post(
        f"/api/v1/obras/{obra_id}/orcamentos", headers=viewer.auth_header, json={"titulo": "X"}
    )
    assert resp.status_code == 403


def test_cross_tenant_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    o_b = _create_orcamento(client, owner_b, obra_b)

    assert (
        client.get(f"/api/v1/orcamentos/{o_b['id']}", headers=owner_a.auth_header).status_code
        == 404
    )
    assert client.get("/api/v1/orcamentos", headers=owner_a.auth_header).json()["items"] == []
