"""B2.3 — CRUD de obras (docs/SPRINTS.md: "Status enum validado,
date_prevista_fim >= data_inicio, busca por cliente/status"; contrato em
docs/ESPEC.md § 7).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from decimal import Decimal

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"
CPF_VALIDO = "11144477735"


def _seed_cliente(
    client: TestClient, owner: SeededUser, *, tipo: str = "PJ", documento: str = CNPJ_VALIDO
) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": tipo, "documento": documento, "nome": "Cliente da Obra"},
    )
    assert resp.status_code == 201
    return str(resp.json()["id"])


def _nova_obra(cliente_id: str, **over: object) -> dict:
    base: dict = {"cliente_id": cliente_id, "codigo": "OBR-001", "nome": "Reforma X"}
    base.update(over)
    return base


def test_create_obra_201_status_default(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    resp = client.post("/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_id))
    assert resp.status_code == 201
    body = resp.json()
    assert uuid.UUID(body["id"])
    assert body["cliente_id"] == cliente_id
    assert body["status"] == "planejamento"


def test_create_status_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, status="em_andamento"),
    )
    assert resp.status_code == 422


def test_create_data_fim_antes_inicio_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, data_inicio="2026-06-01", data_prevista_fim="2026-05-01"),
    )
    assert resp.status_code == 422


def test_create_cliente_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(str(uuid.uuid4()))
    )
    assert resp.status_code == 422


def test_create_cliente_de_outro_tenant_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    cliente_a = _seed_cliente(client, owner_a)
    # B não enxerga o cliente de A (RLS) -> referência é rejeitada com 422.
    resp = client.post("/api/v1/obras", headers=owner_b.auth_header, json=_nova_obra(cliente_a))
    assert resp.status_code == 422


def test_create_sem_permissao_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    # A checagem de role roda como dependency, antes do service — cliente_id
    # qualquer basta para provar o 403.
    viewer = seed_tenant(role="viewer")
    resp = client.post(
        "/api/v1/obras", headers=viewer.auth_header, json=_nova_obra(str(uuid.uuid4()))
    )
    assert resp.status_code == 403


def test_get_por_id_200_e_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    created = client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_id)
    ).json()

    ok = client.get(f"/api/v1/obras/{created['id']}", headers=owner.auth_header)
    assert ok.status_code == 200
    assert ok.json()["id"] == created["id"]

    missing = client.get(f"/api/v1/obras/{uuid.uuid4()}", headers=owner.auth_header)
    assert missing.status_code == 404


def test_patch_status_200(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    created = client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_id)
    ).json()

    resp = client.patch(
        f"/api/v1/obras/{created['id']}",
        headers=owner.auth_header,
        json={"status": "execucao"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "execucao"


def test_patch_data_invalida_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    created = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, data_inicio="2026-06-01"),
    ).json()

    # data_prevista_fim < data_inicio já existente -> 422 (validado no service).
    resp = client.patch(
        f"/api/v1/obras/{created['id']}",
        headers=owner.auth_header,
        json={"data_prevista_fim": "2026-05-01"},
    )
    assert resp.status_code == 422


def test_valor_contrato_precisao(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    created = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, valor_contrato="150000.50"),
    )
    assert created.status_code == 201
    # Aceita serialização como string ou número, mas o valor deve ser exato.
    assert Decimal(str(created.json()["valor_contrato"])) == Decimal("150000.50")


def test_delete_204_soft_delete_some_da_listagem(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    created = client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_id)
    ).json()

    assert (
        client.delete(f"/api/v1/obras/{created['id']}", headers=owner.auth_header).status_code
        == 204
    )
    assert (
        client.get(f"/api/v1/obras/{created['id']}", headers=owner.auth_header).status_code == 404
    )
    listagem = client.get("/api/v1/obras", headers=owner.auth_header).json()
    assert all(item["id"] != created["id"] for item in listagem["items"])
    # Segundo delete -> 404 (já deletado).
    assert (
        client.delete(f"/api/v1/obras/{created['id']}", headers=owner.auth_header).status_code
        == 404
    )


def test_listagem_paginacao_cursor(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    for i in range(3):
        r = client.post(
            "/api/v1/obras",
            headers=owner.auth_header,
            json=_nova_obra(cliente_id, codigo=f"OBR-{i}", nome=f"Obra {i}"),
        )
        assert r.status_code == 201

    page1 = client.get("/api/v1/obras?limit=2", headers=owner.auth_header).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    page2 = client.get(
        f"/api/v1/obras?limit=2&cursor={page1['next_cursor']}", headers=owner.auth_header
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None

    ids = {i["id"] for i in page1["items"]} | {i["id"] for i in page2["items"]}
    assert len(ids) == 3


def test_filtro_por_status(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, codigo="OBR-P"),
    )
    client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json=_nova_obra(cliente_id, codigo="OBR-E", status="execucao"),
    )

    resp = client.get("/api/v1/obras?status=execucao", headers=owner.auth_header).json()
    assert len(resp["items"]) == 1
    assert resp["items"][0]["status"] == "execucao"


def test_filtro_por_cliente(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_pj = _seed_cliente(client, owner, tipo="PJ", documento=CNPJ_VALIDO)
    cliente_pf = _seed_cliente(client, owner, tipo="PF", documento=CPF_VALIDO)
    client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_pj, codigo="OBR-PJ")
    )
    client.post(
        "/api/v1/obras", headers=owner.auth_header, json=_nova_obra(cliente_pf, codigo="OBR-PF")
    )

    resp = client.get(f"/api/v1/obras?cliente_id={cliente_pf}", headers=owner.auth_header).json()
    assert len(resp["items"]) == 1
    assert resp["items"][0]["cliente_id"] == cliente_pf


def test_isolamento_entre_tenants(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    cliente_a = _seed_cliente(client, owner_a)
    client.post("/api/v1/obras", headers=owner_a.auth_header, json=_nova_obra(cliente_a))

    lista_b = client.get("/api/v1/obras", headers=owner_b.auth_header).json()
    assert lista_b["items"] == []
