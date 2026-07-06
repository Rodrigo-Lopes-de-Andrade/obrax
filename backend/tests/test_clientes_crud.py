"""B2.2 — CRUD de clientes (docs/SPRINTS.md: "Validação PF/CNPJ, duplicidade
por documento, busca paginada cursor-based, 200/201/204/404/422", e
"Duplicação documento por company_id retorna 409").
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _cpf(base9: str) -> str:
    """Gera um CPF válido (11 dígitos) a partir de uma base de 9 dígitos."""
    digits = base9
    for length in (9, 10):
        total = sum(int(digits[i]) * (length + 1 - i) for i in range(length))
        digits += str((total * 10) % 11 % 10)
    return digits


def _novo_cliente(nome: str = "Fulano", tipo: str = "PF", documento: str | None = None) -> dict:
    return {
        "tipo_pessoa": tipo,
        "documento": documento or _cpf("111444777"),
        "nome": nome,
    }


def test_create_pf_201_normaliza_documento(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PF", "documento": "111.444.777-35", "nome": "Fulano"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["documento"] == "11144477735"  # só dígitos
    assert uuid.UUID(body["id"])


def test_create_pj_201(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Construtora X"},
    )
    assert resp.status_code == 201


def test_create_documento_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PF", "documento": "12345678900", "nome": "Fulano"},
    )
    assert resp.status_code == 422


def test_create_documento_duplicado_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    payload = _novo_cliente()
    assert (
        client.post("/api/v1/clientes", headers=owner.auth_header, json=payload).status_code == 201
    )
    dup = client.post("/api/v1/clientes", headers=owner.auth_header, json=payload)
    assert dup.status_code == 409


def test_create_sem_permissao_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    viewer = seed_tenant(role="viewer")
    resp = client.post("/api/v1/clientes", headers=viewer.auth_header, json=_novo_cliente())
    assert resp.status_code == 403


def test_get_por_id_200_e_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    created = client.post(
        "/api/v1/clientes", headers=owner.auth_header, json=_novo_cliente()
    ).json()

    ok = client.get(f"/api/v1/clientes/{created['id']}", headers=owner.auth_header)
    assert ok.status_code == 200
    assert ok.json()["id"] == created["id"]

    missing = client.get(f"/api/v1/clientes/{uuid.uuid4()}", headers=owner.auth_header)
    assert missing.status_code == 404


def test_patch_atualiza_nome_200(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    created = client.post(
        "/api/v1/clientes", headers=owner.auth_header, json=_novo_cliente(nome="Antigo")
    ).json()

    resp = client.patch(
        f"/api/v1/clientes/{created['id']}",
        headers=owner.auth_header,
        json={"nome": "Novo Nome"},
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Novo Nome"


def test_delete_204_soft_delete_some_da_listagem(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    created = client.post(
        "/api/v1/clientes", headers=owner.auth_header, json=_novo_cliente()
    ).json()

    assert (
        client.delete(f"/api/v1/clientes/{created['id']}", headers=owner.auth_header).status_code
        == 204
    )
    # Soft delete: GET direto 404 e não aparece na listagem.
    assert (
        client.get(f"/api/v1/clientes/{created['id']}", headers=owner.auth_header).status_code
        == 404
    )
    listagem = client.get("/api/v1/clientes", headers=owner.auth_header).json()
    assert all(item["id"] != created["id"] for item in listagem["items"])
    # Segundo delete → 404 (já deletado).
    assert (
        client.delete(f"/api/v1/clientes/{created['id']}", headers=owner.auth_header).status_code
        == 404
    )


def test_listagem_paginacao_cursor(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    bases = ["100000001", "200000002", "300000003"]
    for i, base in enumerate(bases):
        r = client.post(
            "/api/v1/clientes",
            headers=owner.auth_header,
            json=_novo_cliente(nome=f"Cliente {i}", documento=_cpf(base)),
        )
        assert r.status_code == 201

    page1 = client.get("/api/v1/clientes?limit=2", headers=owner.auth_header).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    page2 = client.get(
        f"/api/v1/clientes?limit=2&cursor={page1['next_cursor']}", headers=owner.auth_header
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None

    ids = {i["id"] for i in page1["items"]} | {i["id"] for i in page2["items"]}
    assert len(ids) == 3


def test_filtro_por_tipo(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json=_novo_cliente(nome="PF", documento=_cpf("111444777")),
    )
    client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "PJ"},
    )

    resp = client.get("/api/v1/clientes?type=PJ", headers=owner.auth_header).json()
    assert len(resp["items"]) == 1
    assert resp["items"][0]["tipo_pessoa"] == "PJ"


def test_cursor_invalido_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.get("/api/v1/clientes?cursor=nao-e-uuid", headers=owner.auth_header)
    assert resp.status_code == 422


def test_isolamento_entre_tenants(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    client.post("/api/v1/clientes", headers=owner_a.auth_header, json=_novo_cliente(nome="Do A"))

    lista_b = client.get("/api/v1/clientes", headers=owner_b.auth_header).json()
    assert lista_b["items"] == []
