"""B6.1 / D6.1 — Curva ABC (US-14): classificação 80/15/5, persistência em
`orcamento_versao.curva_abc_json` no recálculo e endpoint GET curva-abc.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.modules.orcamento.services import curva_abc
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _leaf(valor: str, ident: str) -> dict[str, Any]:
    return {
        "id": uuid.UUID(int=int(ident)),
        "codigo": None,
        "descricao": f"item-{ident}",
        "unidade": "un",
        "custo": Decimal(valor),
    }


# --------------------------------------------------------------------------- #
# Classificador puro (sem banco)
# --------------------------------------------------------------------------- #
def test_classificacao_80_15_5() -> None:
    """A concentra ~80% do custo, B os 15% seguintes, C os 5% finais."""
    leaves = [
        _leaf("800.00", "1"),  # 80%
        _leaf("100.00", "2"),  # 80→90%  → B
        _leaf("50.00", "3"),  # 90→95%   → B
        _leaf("30.00", "4"),  # 95→98%   → C
        _leaf("15.00", "5"),  # 98→99.5% → C
        _leaf("5.00", "6"),  # 99.5→100% → C
    ]
    curva = curva_abc.classificar(leaves)

    assert curva.custo_total == Decimal("1000.00")
    por_classe = {c.classe: c for c in curva.classes}
    assert por_classe["A"].count == 1 and por_classe["A"].pct == Decimal("0.8000")
    assert por_classe["B"].count == 2 and por_classe["B"].pct == Decimal("0.1500")
    assert por_classe["C"].count == 3 and por_classe["C"].pct == Decimal("0.0500")

    # Itens ordenados por custo desc; o de maior custo é sempre A.
    assert curva.itens[0].custo == Decimal("800.00")
    assert curva.itens[0].classe == "A"
    assert curva.itens[0].pct_acumulado == Decimal("0.8000")
    assert curva.itens[-1].pct_acumulado == Decimal("1.0000")


def test_item_dominante_e_sempre_A() -> None:
    """Item único que sozinho passa de 80% ainda cai em A (custo acumulado antes = 0)."""
    curva = curva_abc.classificar([_leaf("900.00", "1"), _leaf("100.00", "2")])
    itens = {it.custo: it.classe for it in curva.itens}
    assert itens[Decimal("900.00")] == "A"


def test_curva_vazia() -> None:
    curva = curva_abc.classificar([])
    assert curva.custo_total == Decimal("0")
    assert curva.itens == []
    # As três classes sempre presentes (contagem 0) para a UI renderizar o resumo.
    assert {c.classe for c in curva.classes} == {"A", "B", "C"}
    assert all(c.count == 0 for c in curva.classes)


# --------------------------------------------------------------------------- #
# Persistência via recálculo + endpoint (via API)
# --------------------------------------------------------------------------- #
def _bulk(client: TestClient, owner: SeededUser, vid: str, itens: list[dict]) -> dict:
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": itens},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _orcamento_com_insumos(
    client: TestClient, owner: SeededUser, insumos: list[dict]
) -> tuple[str, str]:
    """Cria obra + orçamento + Fase→Serviço→(insumos) e devolve (orcamento_id, versao_id)."""
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
    vid = orc["versao"]["id"]

    tree = _bulk(client, owner, vid, [{"tipo": "F", "descricao": "Fase"}])
    fase = tree["itens"][0]
    tree = _bulk(
        client, owner, vid, [{"tipo": "S", "descricao": "Serviço", "parent_id": fase["id"]}]
    )
    serv = next(i for i in tree["itens"] if i["tipo"] == "S")
    _bulk(client, owner, vid, [{**i, "tipo": "I", "parent_id": serv["id"]} for i in insumos])
    return orc["id"], vid


def test_recalc_persiste_curva_abc(client: TestClient, seed_tenant: SeedTenant) -> None:
    """D6.1 — toda mutação recalcula e denormaliza a curva em curva_abc_json."""
    owner = seed_tenant(role="owner")
    # 3 insumos: 800 / 150 / 50 (total 1000) → A(80%) / B(15%) / C(5%).
    _, vid = _orcamento_com_insumos(
        client,
        owner,
        [
            {"descricao": "grande", "quantidade": "800", "preco_unitario": "1"},
            {"descricao": "medio", "quantidade": "150", "preco_unitario": "1"},
            {"descricao": "pequeno", "quantidade": "50", "preco_unitario": "1"},
        ],
    )

    with SessionLocal() as session:
        raw = session.execute(
            text("SELECT curva_abc_json FROM orcamento_versao WHERE id = :v"), {"v": vid}
        ).scalar_one()
    assert raw is not None
    assert Decimal(raw["custo_total"]) == Decimal("1000.00")
    classes = {c["classe"]: c for c in raw["classes"]}
    assert classes["A"]["count"] == 1
    assert Decimal(classes["A"]["pct"]) == Decimal("0.8000")


def test_endpoint_curva_abc(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    orcamento_id, _ = _orcamento_com_insumos(
        client,
        owner,
        [
            {"descricao": "Caro", "quantidade": "8", "preco_unitario": "100"},
            {"descricao": "Barato", "quantidade": "2", "preco_unitario": "10"},
        ],
    )

    resp = client.get(f"/api/v1/orcamentos/{orcamento_id}/curva-abc", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["custo_total"] == "820.00"
    caro = next(it for it in body["itens"] if it["descricao"] == "Caro")
    assert caro["classe"] == "A"
    assert body["itens"][0]["descricao"] == "Caro"  # ordenado por custo desc


def test_endpoint_curva_abc_vazia(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Versão sem itens → curva vazia (não 404)."""
    owner = seed_tenant(role="owner")
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

    resp = client.get(f"/api/v1/orcamentos/{orc['id']}/curva-abc", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["custo_total"] == "0"
