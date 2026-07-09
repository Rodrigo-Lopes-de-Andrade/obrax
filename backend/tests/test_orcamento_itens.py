"""B5.4 — itens da EAP (US-12): bulk, PATCH, DELETE, reordenar, duplicar,
precificação; recalc dispara em toda mutação; validação de hierarquia e lock.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _seed_versao(client: TestClient, owner: SeededUser) -> str:
    """Cria obra + orçamento e devolve o id da versão 1."""
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
    orc = client.post(
        f"/api/v1/obras/{obra['id']}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orç"},
    ).json()
    return str(orc["versao"]["id"])


def _bulk(client: TestClient, owner: SeededUser, vid: str, itens: list[dict]) -> dict:
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": itens},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _por_tipo(tree: dict, tipo: str) -> list[dict]:
    return [i for i in tree["itens"] if i["tipo"] == tipo]


def _build_fsi(client: TestClient, owner: SeededUser, vid: str) -> dict:
    """Monta Fase→Serviço→Insumo(qtd 10 × 100,00) e devolve a árvore final."""
    tree = _bulk(client, owner, vid, [{"tipo": "F", "descricao": "Fundações"}])
    fase = _por_tipo(tree, "F")[0]
    tree = _bulk(
        client, owner, vid, [{"tipo": "S", "descricao": "Sapata", "parent_id": fase["id"]}]
    )
    serv = _por_tipo(tree, "S")[0]
    return _bulk(
        client,
        owner,
        vid,
        [
            {
                "tipo": "I",
                "descricao": "Concreto",
                "parent_id": serv["id"],
                "unidade": "m³",
                "quantidade": "10",
                "preco_unitario": "100.00",
            }
        ],
    )


def test_bulk_monta_hierarquia_e_recalcula(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)

    assert len(tree["itens"]) == 3
    insumo = _por_tipo(tree, "I")[0]
    assert insumo["custo_total"] == "1000.00"
    assert insumo["subtotal"] == "1000.00"  # markup global 0
    assert insumo["depth"] == 2
    # Agregou bottom-up: serviço e fase carregam o subtotal do insumo.
    assert _por_tipo(tree, "S")[0]["subtotal"] == "1000.00"
    assert _por_tipo(tree, "F")[0]["subtotal"] == "1000.00"
    assert tree["versao"]["custo_direto"] == "1000.00"
    assert tree["versao"]["preco_venda"] == "1000.00"


def test_precificacao_aplica_markup_e_taxa(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    _build_fsi(client, owner, vid)

    resp = client.put(
        f"/api/v1/orcamentos/versoes/{vid}/precificacao",
        headers=owner.auth_header,
        json={"markup_global": "0.20", "taxa_adm": "0.05"},
    )
    assert resp.status_code == 200, resp.text
    tree = resp.json()
    assert _por_tipo(tree, "I")[0]["subtotal"] == "1200.00"  # 1000 × 1.20
    assert tree["versao"]["custo_direto"] == "1000.00"
    assert tree["versao"]["preco_venda"] == "1260.00"  # 1200 × 1.05
    assert tree["versao"]["markup_global"] == "0.2000"


def test_patch_quantidade_recalcula(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    insumo = _por_tipo(tree, "I")[0]

    resp = client.patch(
        f"/api/v1/orcamentos/itens/{insumo['id']}",
        headers=owner.auth_header,
        json={"quantidade": "5"},
    )
    assert resp.status_code == 200, resp.text
    tree = resp.json()
    assert _por_tipo(tree, "I")[0]["custo_total"] == "500.00"
    assert tree["versao"]["preco_venda"] == "500.00"


def test_patch_sem_campos_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    insumo = _por_tipo(tree, "I")[0]
    resp = client.patch(
        f"/api/v1/orcamentos/itens/{insumo['id']}", headers=owner.auth_header, json={}
    )
    assert resp.status_code == 422


def test_delete_cascateia_subarvore(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    fase = _por_tipo(tree, "F")[0]

    resp = client.delete(f"/api/v1/orcamentos/itens/{fase['id']}", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    tree = resp.json()
    assert tree["itens"] == []  # fase + serviço + insumo removidos
    assert tree["versao"]["preco_venda"] == "0.00"


def test_duplicar_item_clona_subarvore(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    serv = _por_tipo(tree, "S")[0]

    resp = client.post(f"/api/v1/orcamentos/itens/{serv['id']}/duplicar", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    tree = resp.json()
    # serviço duplicado + seu insumo → 2 serviços, 2 insumos, 1 fase = 5 itens
    assert len(_por_tipo(tree, "S")) == 2
    assert len(_por_tipo(tree, "I")) == 2
    assert tree["versao"]["custo_direto"] == "2000.00"  # 1000 + 1000


def test_reorder_move_entre_fases(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    serv = _por_tipo(tree, "S")[0]
    # nova fase de destino
    tree = _bulk(client, owner, vid, [{"tipo": "F", "descricao": "Fase 2"}])
    fase2 = [f for f in _por_tipo(tree, "F") if f["descricao"] == "Fase 2"][0]

    resp = client.put(
        f"/api/v1/orcamentos/versoes/{vid}/itens/ordem",
        headers=owner.auth_header,
        json={"itens": [{"id": serv["id"], "parent_id": fase2["id"], "sort_order": 0}]},
    )
    assert resp.status_code == 200, resp.text
    tree = resp.json()
    movido = next(i for i in tree["itens"] if i["id"] == serv["id"])
    assert movido["parent_id"] == fase2["id"]
    assert movido["path"].startswith(fase2["id"])  # path reindexado sob a fase 2


def test_hierarquia_invalida_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _bulk(client, owner, vid, [{"tipo": "F", "descricao": "Fase"}])
    fase = _por_tipo(tree, "F")[0]

    # insumo direto sob fase (falta serviço)
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": [{"tipo": "I", "descricao": "X", "parent_id": fase["id"]}]},
    )
    assert resp.status_code == 422
    # serviço sem pai
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": [{"tipo": "S", "descricao": "X"}]},
    )
    assert resp.status_code == 422
    # fase com pai
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": [{"tipo": "F", "descricao": "X", "parent_id": fase["id"]}]},
    )
    assert resp.status_code == 422


def test_versao_travada_bloqueia_mutacao_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    tree = _build_fsi(client, owner, vid)
    orc_id = client.get("/api/v1/orcamentos", headers=owner.auth_header).json()["items"][0]["id"]

    # aprova (trava a versão): rascunho → aguardando_aprovacao → aprovado
    client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aguardando_aprovacao"},
    )
    client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aprovado"},
    )

    insumo = _por_tipo(tree, "I")[0]
    assert (
        client.patch(
            f"/api/v1/orcamentos/itens/{insumo['id']}",
            headers=owner.auth_header,
            json={"quantidade": "1"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
            headers=owner.auth_header,
            json={"itens": [{"tipo": "F", "descricao": "Nova"}]},
        ).status_code
        == 409
    )


def test_write_roles_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    vid = _seed_versao(client, owner)
    viewer = seed_tenant(role="viewer")
    assert (
        client.post(
            f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
            headers=viewer.auth_header,
            json={"itens": [{"tipo": "F", "descricao": "X"}]},
        ).status_code
        == 403
    )


def test_cross_tenant_versao_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    vid_b = _seed_versao(client, owner_b)
    resp = client.get(f"/api/v1/orcamentos/versoes/{vid_b}/itens", headers=owner_a.auth_header)
    assert resp.status_code == 404
