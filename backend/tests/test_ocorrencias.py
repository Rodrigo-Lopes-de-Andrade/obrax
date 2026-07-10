"""B8.4 — CRUD de ocorrências de campo (foto obrigatória, GPS opcional; US-18).

O vínculo de fotos usa `photo.ocorrencia_id`; as fotos só precisam existir
(estado `pendente` basta) para serem ligadas — o sync não toca no storage
(presigned é assinatura local), então estes testes não dependem do MinIO.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from starlette.testclient import TestClient

from app.core.security import create_access_token
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"
CAPTURED_AT = "2026-07-10T12:00:00Z"


def _seed_cliente(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente da Obra"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _seed_obra(
    client: TestClient,
    owner: SeededUser,
    *,
    cliente_id: str | None = None,
    codigo: str = "OBR-001",
) -> str:
    # Reusa um cliente (o `documento` é único por tenant — não dá p/ recriar).
    cliente_id = cliente_id or _seed_cliente(client, owner)
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente_id, "codigo": codigo, "nome": "Reforma X"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _sync_photo(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    """Sincroniza uma foto pendente (conteúdo único p/ não bater no dedup) e
    devolve o `photo_id`."""
    sha = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars, único por chamada
    resp = client.post(
        "/api/v1/photos/sync",
        headers={**owner.auth_header, "Idempotency-Key": str(uuid.uuid4())},
        json={"obra_id": obra_id, "sha256": sha, "size_bytes": 1234, "captured_at": CAPTURED_AT},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["photo_id"])


def test_criar_ocorrencia_com_foto(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)

    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={
            "titulo": "Infiltração na laje",
            "descricao": "Mancha de umidade crescente no teto do 2º andar.",
            "gps_lat": -23.55052,
            "gps_lng": -46.633308,
            "photo_ids": [pid],
        },
    )
    assert resp.status_code == 201, resp.text
    oc = resp.json()
    assert oc["titulo"] == "Infiltração na laje"
    assert oc["status"] == "aberto"
    assert oc["photo_ids"] == [pid]
    assert oc["gps_lat"] == -23.55052
    assert oc["gps_lng"] == -46.633308


def test_foto_obrigatoria_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Sem foto", "photo_ids": []},
    )
    assert resp.status_code == 422


def test_foto_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Foto fantasma", "photo_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 422


def test_foto_de_outra_obra_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    obra1 = _seed_obra(client, owner, cliente_id=cliente_id, codigo="OBR-1")
    obra2 = _seed_obra(client, owner, cliente_id=cliente_id, codigo="OBR-2")
    pid = _sync_photo(client, owner, obra1)
    # Vincular foto da obra1 numa ocorrência da obra2 → 422 (escopo por obra).
    resp = client.post(
        f"/api/v1/obras/{obra2}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Foto de outra obra", "photo_ids": [pid]},
    )
    assert resp.status_code == 422


def test_foto_ja_vinculada_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)
    r1 = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Primeira", "photo_ids": [pid]},
    )
    assert r1.status_code == 201
    # Mesma foto já ligada à primeira ocorrência → 422 na segunda.
    r2 = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Segunda", "photo_ids": [pid]},
    )
    assert r2.status_code == 422


def test_gps_opcional(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Sem GPS", "photo_ids": [pid]},
    )
    assert resp.status_code == 201, resp.text
    oc = resp.json()
    assert oc["gps_lat"] is None and oc["gps_lng"] is None


def test_gps_fora_de_faixa_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "GPS inválido", "gps_lat": 100, "photo_ids": [pid]},
    )
    assert resp.status_code == 422


def test_patch_status(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)
    oc_id = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers=owner.auth_header,
        json={"titulo": "Resolver", "photo_ids": [pid]},
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/ocorrencias/{oc_id}", headers=owner.auth_header, json={"status": "resolvido"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "resolvido"


def test_list_e_get(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ids = []
    for i in range(2):
        pid = _sync_photo(client, owner, obra_id)
        ids.append(
            client.post(
                f"/api/v1/obras/{obra_id}/ocorrencias",
                headers=owner.auth_header,
                json={"titulo": f"Ocorrência {i}", "photo_ids": [pid]},
            ).json()["id"]
        )

    page = client.get(f"/api/v1/obras/{obra_id}/ocorrencias", headers=owner.auth_header).json()
    # Mais recentes primeiro (id v7 ~ tempo).
    assert [o["id"] for o in page["items"]] == [ids[1], ids[0]]

    got = client.get(f"/api/v1/ocorrencias/{ids[0]}", headers=owner.auth_header)
    assert got.status_code == 200
    assert got.json()["id"] == ids[0]


def test_viewer_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    viewer = seed_tenant(role="viewer")
    resp = client.post(
        f"/api/v1/obras/{uuid.uuid4()}/ocorrencias",
        headers=viewer.auth_header,
        json={"titulo": "x", "photo_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 403


def test_campo_pode_registrar(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    pid = _sync_photo(client, owner, obra_id)
    campo_token = create_access_token(
        user_id=uuid.UUID(owner.user_id),
        company_id=uuid.UUID(owner.company_id),
        role="campo",
    ).token
    resp = client.post(
        f"/api/v1/obras/{obra_id}/ocorrencias",
        headers={"Authorization": f"Bearer {campo_token}"},
        json={"titulo": "Registrada em campo", "photo_ids": [pid]},
    )
    assert resp.status_code == 201, resp.text


def test_cross_tenant_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    # Tenant A não enxerga a obra de B (RLS) → list 404, create 422.
    assert (
        client.get(f"/api/v1/obras/{obra_b}/ocorrencias", headers=owner_a.auth_header).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/obras/{obra_b}/ocorrencias",
            headers=owner_a.auth_header,
            json={"titulo": "intruso", "photo_ids": [str(uuid.uuid4())]},
        ).status_code
        == 422
    )
