"""B3.3 — CRUD de documento: listagem paginada (+filtro categoria), PATCH de
categoria/visibilidade (US-06) e soft delete. Contrato em docs/ESPEC.md § 6.

Não confirma uploads (não precisa do storage): a linha existe assim que o
create roda, e list/patch/delete operam sobre ela (`confirmed=false`).
"""

from __future__ import annotations

import hashlib
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
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente da Obra"},
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-001", "nome": "Reforma X"},
    )
    assert resp.status_code == 201
    return str(resp.json()["id"])


def _create_doc(
    client: TestClient,
    owner: SeededUser,
    obra_id: str,
    *,
    categoria: str | None = None,
    nome: str = "doc.pdf",
) -> str:
    # sha256 único por documento — UNIQUE (obra_id, sha256) proíbe repetição.
    body: dict = {
        "nome": nome,
        "tipo": "outro",
        "sha256": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "size_bytes": 10,
    }
    if categoria is not None:
        body["categoria"] = categoria
    resp = client.post(f"/api/v1/obras/{obra_id}/documentos", headers=owner.auth_header, json=body)
    assert resp.status_code == 201
    return str(resp.json()["documento_id"])


def test_list_paginacao(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ids = {_create_doc(client, owner, obra_id) for _ in range(3)}

    resp = client.get(f"/api/v1/obras/{obra_id}/documentos?limit=2", headers=owner.auth_header)
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    assert all(item["confirmed"] is False for item in page1["items"])

    resp = client.get(
        f"/api/v1/obras/{obra_id}/documentos?limit=2&cursor={page1['next_cursor']}",
        headers=owner.auth_header,
    )
    page2 = resp.json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None
    seen = {item["id"] for item in page1["items"] + page2["items"]}
    assert seen == ids


def test_list_filtro_categoria(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_a = _create_doc(client, owner, obra_id, categoria="Projetos")
    _create_doc(client, owner, obra_id, categoria="Contratos")

    resp = client.get(
        f"/api/v1/obras/{obra_id}/documentos?categoria=Projetos", headers=owner.auth_header
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [item["id"] for item in items] == [doc_a]


def test_patch_categoria_e_visibilidade(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)

    resp = client.patch(
        f"/api/v1/documentos/{doc_id}",
        headers=owner.auth_header,
        json={"categoria": "Contratos", "visivel_cliente": True},
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["categoria"] == "Contratos"
    assert doc["visivel_cliente"] is True


def test_patch_vazio_noop(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)

    resp = client.patch(f"/api/v1/documentos/{doc_id}", headers=owner.auth_header, json={})
    assert resp.status_code == 200
    assert resp.json()["visivel_cliente"] is False


def test_patch_documento_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.patch(
        f"/api/v1/documentos/{uuid.uuid4()}",
        headers=owner.auth_header,
        json={"visivel_cliente": True},
    )
    assert resp.status_code == 404


def test_delete_soft_some_da_lista(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)

    resp = client.delete(f"/api/v1/documentos/{doc_id}", headers=owner.auth_header)
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/obras/{obra_id}/documentos", headers=owner.auth_header)
    assert [item["id"] for item in resp.json()["items"]] == []

    # Já removido: PATCH e novo DELETE → 404.
    assert (
        client.patch(
            f"/api/v1/documentos/{doc_id}",
            headers=owner.auth_header,
            json={"visivel_cliente": True},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/documentos/{doc_id}", headers=owner.auth_header).status_code == 404
    )


def test_write_roles_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)
    viewer = seed_tenant(role="viewer")

    assert (
        client.patch(
            f"/api/v1/documentos/{doc_id}",
            headers=viewer.auth_header,
            json={"visivel_cliente": True},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/documentos/{doc_id}", headers=viewer.auth_header).status_code == 403
    )


def test_list_obra_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.get(f"/api/v1/obras/{uuid.uuid4()}/documentos", headers=owner.auth_header)
    assert resp.status_code == 404


def test_cross_tenant_isolado(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    doc_b = _create_doc(client, owner_b, obra_b)

    # A não enxerga a obra de B → 404 na listagem; nem o documento → 404 no PATCH.
    assert (
        client.get(f"/api/v1/obras/{obra_b}/documentos", headers=owner_a.auth_header).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/documentos/{doc_b}",
            headers=owner_a.auth_header,
            json={"visivel_cliente": True},
        ).status_code
        == 404
    )
