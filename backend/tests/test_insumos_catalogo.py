"""B5.6 / D5.2 — catálogo de insumos: gerador SINAPI, busca/autocomplete,
filtro por categoria, paginação por cursor, RLS (global + custom) e perf <500ms.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.modules.orcamento.catalog_sinapi import gerar_catalogo
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

_INSERT_GLOBAL = text(
    "INSERT INTO insumo (company_id, codigo, descricao, unidade, categoria, preco_unitario) "
    "VALUES (NULL, :codigo, :descricao, :unidade, :categoria, :preco)"
)
# Marcador "ZULU" nas descrições + categorias prefixadas "TST-" garantem que os
# testes não colidam com o catálogo SINAPI real (que pode estar semeado no banco).
_KNOWN = [
    {
        "codigo": "TST-001",
        "descricao": "Concreto usinadoZULU fck 30MPa",
        "unidade": "m³",
        "categoria": "TST-Concreto",
        "preco": "550.00",
    },
    {
        "codigo": "TST-002",
        "descricao": "Bloco cerâmicoZULU 14x19x39",
        "unidade": "m²",
        "categoria": "TST-Alvenaria",
        "preco": "65.00",
    },
    {
        "codigo": "TST-003",
        "descricao": "Tinta acrílicaZULU premium",
        "unidade": "m²",
        "categoria": "TST-Pintura",
        "preco": "32.00",
    },
    {
        "codigo": "TST-004",
        "descricao": "PorcelanatoZULU polido 80x80",
        "unidade": "m²",
        "categoria": "TST-Revestimentos",
        "preco": "190.00",
    },
]


@pytest.fixture
def insumos_globais() -> Iterator[None]:
    with SessionLocal() as session:
        session.execute(_INSERT_GLOBAL, _KNOWN)
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(text("DELETE FROM insumo WHERE codigo LIKE 'TST-%'"))
        session.commit()


# --------------------------------------------------------------------------- #
# Gerador (puro, sem DB)
# --------------------------------------------------------------------------- #
def test_gerar_catalogo_determinístico_e_unico() -> None:
    itens = list(gerar_catalogo(500))
    assert len(itens) == 500
    codigos = {i.codigo for i in itens}
    assert len(codigos) == 500  # todos únicos
    assert all(i.preco_unitario > 0 and i.categoria and i.unidade for i in itens)
    # Determinístico: mesma semente → mesma primeira linha.
    assert list(gerar_catalogo(1))[0] == itens[0]


def test_gerar_catalogo_dez_mil() -> None:
    codigos = {i.codigo for i in gerar_catalogo(10_000)}
    assert len(codigos) == 10_000


# --------------------------------------------------------------------------- #
# Busca / autocomplete (API, sob RLS)
# --------------------------------------------------------------------------- #
def test_busca_por_descricao(
    client: TestClient, seed_tenant: SeedTenant, insumos_globais: None
) -> None:
    owner = seed_tenant(role="owner")
    resp = client.get("/api/v1/insumos?search=ZULU", headers=owner.auth_header)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {i["codigo"] for i in items} == {"TST-001", "TST-002", "TST-003", "TST-004"}
    assert all(i["is_custom"] is False for i in items)  # catálogo global


def test_busca_por_codigo(
    client: TestClient, seed_tenant: SeedTenant, insumos_globais: None
) -> None:
    owner = seed_tenant(role="owner")
    items = client.get("/api/v1/insumos?search=TST-002", headers=owner.auth_header).json()["items"]
    assert [i["codigo"] for i in items] == ["TST-002"]


def test_filtro_categoria(
    client: TestClient, seed_tenant: SeedTenant, insumos_globais: None
) -> None:
    owner = seed_tenant(role="owner")
    items = client.get("/api/v1/insumos?categoria=TST-Pintura", headers=owner.auth_header).json()[
        "items"
    ]
    assert [i["codigo"] for i in items] == ["TST-003"]


def test_categorias_endpoint(
    client: TestClient, seed_tenant: SeedTenant, insumos_globais: None
) -> None:
    owner = seed_tenant(role="owner")
    cats = client.get("/api/v1/insumos/categorias", headers=owner.auth_header).json()["categorias"]
    assert {"TST-Concreto", "TST-Alvenaria", "TST-Pintura", "TST-Revestimentos"} <= set(cats)
    assert cats == sorted(cats)  # ordenado


def test_cursor_paginacao(
    client: TestClient, seed_tenant: SeedTenant, insumos_globais: None
) -> None:
    owner = seed_tenant(role="owner")
    p1 = client.get("/api/v1/insumos?search=TST&limit=2", headers=owner.auth_header).json()
    assert len(p1["items"]) == 2
    assert p1["next_cursor"] is not None
    p2 = client.get(
        f"/api/v1/insumos?search=TST&limit=2&cursor={p1['next_cursor']}",
        headers=owner.auth_header,
    ).json()
    ids1 = {i["id"] for i in p1["items"]}
    ids2 = {i["id"] for i in p2["items"]}
    assert ids1.isdisjoint(ids2)  # páginas não se sobrepõem


def test_insumo_custom_isolado_por_tenant(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Insumo com company_id do tenant A: visível para A, invisível para B; o
    global (NULL) é visível para ambos."""
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO insumo (company_id, codigo, descricao, categoria, preco_unitario) "
                "VALUES (CAST(:cid AS uuid), 'CUSTOM-A', 'Insumo exclusivo A', 'Especial', 10)"
            ),
            {"cid": owner_a.company_id},
        )
        session.commit()
    try:
        a = client.get("/api/v1/insumos?search=exclusivo", headers=owner_a.auth_header).json()
        b = client.get("/api/v1/insumos?search=exclusivo", headers=owner_b.auth_header).json()
        assert [i["codigo"] for i in a["items"]] == ["CUSTOM-A"]
        assert a["items"][0]["is_custom"] is True
        assert b["items"] == []
    finally:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM insumo WHERE codigo = 'CUSTOM-A'"))
            session.commit()


def test_busca_sub_500ms(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Critério B5.6: busca por descrição <500ms num catálogo grande."""
    owner = seed_tenant(role="owner")
    rows = [
        {
            "codigo": f"TSTPERF-{i:06d}",
            "descricao": ins.descricao,
            "unidade": ins.unidade,
            "categoria": ins.categoria,
            "preco": str(ins.preco_unitario),
        }
        for i, ins in enumerate(gerar_catalogo(4000))
    ]
    with SessionLocal() as session:
        session.execute(_INSERT_GLOBAL, rows)
        session.commit()
    try:
        start = time.perf_counter()
        resp = client.get("/api/v1/insumos?search=porcelanato&limit=20", headers=owner.auth_header)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert len(resp.json()["items"]) > 0
        assert elapsed < 0.5, f"busca levou {elapsed * 1000:.0f}ms (alvo <500ms)"
    finally:
        with SessionLocal() as session:
            session.execute(text("DELETE FROM insumo WHERE codigo LIKE 'TSTPERF-%'"))
            session.commit()
