"""B7.2 — checklist de campo (US-16): CRUD, toggle com carimbo de completed_at,
ordenação/paginação por sort_order, soft delete e RBAC.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _criar_obra(client: TestClient, owner: SeededUser) -> str:
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": "OBR-1", "nome": "Obra"},
    ).json()
    return obra["id"]


def _add(client: TestClient, owner: SeededUser, obra_id: str, titulo: str) -> dict:
    resp = client.post(
        f"/api/v1/obras/{obra_id}/checklist",
        headers=owner.auth_header,
        json={"titulo": titulo},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_criar_e_listar_ordenado(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    for t in ["Conferir EPIs", "Registrar avanço", "Limpeza do canteiro"]:
        _add(client, owner, obra_id, t)

    body = client.get(f"/api/v1/obras/{obra_id}/checklist", headers=owner.auth_header).json()
    assert [i["titulo"] for i in body["items"]] == [
        "Conferir EPIs",
        "Registrar avanço",
        "Limpeza do canteiro",
    ]
    # sort_order incremental a partir de 0; nascem não concluídos.
    assert [i["sort_order"] for i in body["items"]] == [0, 1, 2]
    assert all(i["completed"] is False and i["completed_at"] is None for i in body["items"])
    assert body["next_cursor"] is None


def test_toggle_carimba_completed_at(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    item = _add(client, owner, obra_id, "Conferir EPIs")

    done = client.patch(
        f"/api/v1/checklist/{item['id']}",
        headers=owner.auth_header,
        json={"completed": True},
    ).json()
    assert done["completed"] is True
    assert done["completed_at"] is not None

    undone = client.patch(
        f"/api/v1/checklist/{item['id']}",
        headers=owner.auth_header,
        json={"completed": False},
    ).json()
    assert undone["completed"] is False
    assert undone["completed_at"] is None


def test_editar_titulo(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    item = _add(client, owner, obra_id, "Titulo antigo")

    resp = client.patch(
        f"/api/v1/checklist/{item['id']}",
        headers=owner.auth_header,
        json={"titulo": "Titulo novo"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["titulo"] == "Titulo novo"


def test_patch_vazio_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    item = _add(client, owner, obra_id, "Item")
    resp = client.patch(f"/api/v1/checklist/{item['id']}", headers=owner.auth_header, json={})
    assert resp.status_code == 422, resp.text


def test_soft_delete(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    item = _add(client, owner, obra_id, "Item")

    resp = client.delete(f"/api/v1/checklist/{item['id']}", headers=owner.auth_header)
    assert resp.status_code == 204, resp.text

    body = client.get(f"/api/v1/obras/{obra_id}/checklist", headers=owner.auth_header).json()
    assert body["items"] == []
    # Re-excluir um item já removido → 404.
    assert (
        client.delete(f"/api/v1/checklist/{item['id']}", headers=owner.auth_header).status_code
        == 404
    )


def test_paginacao_keyset(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    for i in range(5):
        _add(client, owner, obra_id, f"Item {i}")

    page1 = client.get(
        f"/api/v1/obras/{obra_id}/checklist?limit=2", headers=owner.auth_header
    ).json()
    assert [i["titulo"] for i in page1["items"]] == ["Item 0", "Item 1"]
    assert page1["next_cursor"] is not None

    page2 = client.get(
        f"/api/v1/obras/{obra_id}/checklist?limit=2&cursor={page1['next_cursor']}",
        headers=owner.auth_header,
    ).json()
    assert [i["titulo"] for i in page2["items"]] == ["Item 2", "Item 3"]

    page3 = client.get(
        f"/api/v1/obras/{obra_id}/checklist?limit=2&cursor={page2['next_cursor']}",
        headers=owner.auth_header,
    ).json()
    assert [i["titulo"] for i in page3["items"]] == ["Item 4"]
    assert page3["next_cursor"] is None


def test_obra_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    fake = "00000000-0000-0000-0000-000000000000"
    assert (
        client.get(f"/api/v1/obras/{fake}/checklist", headers=owner.auth_header).status_code == 404
    )
    resp = client.post(
        f"/api/v1/obras/{fake}/checklist", headers=owner.auth_header, json={"titulo": "x"}
    )
    assert resp.status_code == 404, resp.text


def test_cursor_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    resp = client.get(
        f"/api/v1/obras/{obra_id}/checklist?cursor=nao-e-uuid", headers=owner.auth_header
    )
    assert resp.status_code == 422, resp.text


def test_viewer_nao_escreve(client: TestClient, seed_tenant: SeedTenant) -> None:
    """`viewer` (sem permissão de escrita) não cria itens → 403."""
    owner = seed_tenant(role="owner")
    viewer = seed_tenant(role="viewer")
    obra_id = _criar_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/checklist",
        headers=viewer.auth_header,
        json={"titulo": "x"},
    )
    assert resp.status_code == 403, resp.text
