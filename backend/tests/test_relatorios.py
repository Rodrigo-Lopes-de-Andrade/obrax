"""B6.5 — relatórios gerenciais (US-10): agregações por status de obras e
orçamentos, isoladas por tenant (RLS), com breakdown zero-preenchido. O cache é
sobrescrito por `NoopCache` para asserir sempre o estado atual do banco.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.integrations.cache import NoopCache, get_relatorios_cache
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


@pytest.fixture
def no_cache() -> Iterator[None]:
    app.dependency_overrides[get_relatorios_cache] = NoopCache
    yield
    app.dependency_overrides.pop(get_relatorios_cache, None)


def _seed_obras(company_id: str) -> None:
    """3 obras: execucao 1000, planejamento 500, concluida 9999 — via `obrax`."""
    with SessionLocal() as session:
        cliente_id = session.execute(
            text(
                "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                "VALUES (:cid, 'PJ', :doc, 'Cliente') RETURNING id"
            ),
            {"cid": company_id, "doc": CNPJ_VALIDO},
        ).scalar_one()
        for codigo, status, valor in [
            ("A", "execucao", "1000.00"),
            ("B", "planejamento", "500.00"),
            ("C", "concluida", "9999.00"),
        ]:
            session.execute(
                text(
                    "INSERT INTO obras "
                    "(company_id, cliente_id, codigo, nome, status, valor_contrato) "
                    "VALUES (:cid, :cli, :cod, :nome, CAST(:st AS obra_status), :val)"
                ),
                {
                    "cid": company_id,
                    "cli": cliente_id,
                    "cod": codigo,
                    "nome": f"Obra {codigo}",
                    "st": status,
                    "val": valor,
                },
            )
        session.commit()


def _criar_obra(client: TestClient, owner: SeededUser) -> str:
    """Cliente + obra (uma vez por tenant — o CNPJ é único por empresa)."""
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cli"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": "OBR", "nome": "Obra"},
    ).json()
    return obra["id"]


def _criar_orcamento(
    client: TestClient, owner: SeededUser, obra_id: str, *, status: str | None
) -> str:
    """Cria um orçamento na obra; opcionalmente transiciona pro `status`."""
    orc = client.post(
        f"/api/v1/obras/{obra_id}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orç"},
    ).json()
    if status is not None:
        resp = client.patch(
            f"/api/v1/orcamentos/{orc['id']}/status",
            headers=owner.auth_header,
            json={"status": status},
        )
        assert resp.status_code == 200, resp.text
    return orc["id"]


# --------------------------------------------------------------------------- #
# Obras ativas
# --------------------------------------------------------------------------- #
def test_obras_ativas_agrega(client: TestClient, seed_tenant: SeedTenant, no_cache: None) -> None:
    owner = seed_tenant(role="owner")
    _seed_obras(owner.company_id)

    body = client.get("/api/v1/relatorios/obras-ativas", headers=owner.auth_header).json()
    assert body["ativas"] == 2  # execucao + planejamento
    assert Decimal(body["valor_ativas"]) == Decimal("1500.00")
    assert body["total"] == 3
    # Breakdown zero-preenchido: os 5 status sempre presentes, na ordem do enum.
    por = {ln["status"]: ln for ln in body["por_status"]}
    assert [ln["status"] for ln in body["por_status"]] == [
        "planejamento",
        "execucao",
        "pausada",
        "concluida",
        "cancelada",
    ]
    assert por["execucao"]["count"] == 1
    assert Decimal(por["concluida"]["valor"]) == Decimal("9999.00")
    assert por["cancelada"]["count"] == 0
    assert Decimal(por["pausada"]["valor"]) == Decimal("0.00")


def test_obras_ativas_vazio(client: TestClient, seed_tenant: SeedTenant, no_cache: None) -> None:
    owner = seed_tenant(role="owner")
    body = client.get("/api/v1/relatorios/obras-ativas", headers=owner.auth_header).json()
    assert body["ativas"] == 0
    assert Decimal(body["valor_ativas"]) == Decimal("0.00")
    assert len(body["por_status"]) == 5
    assert all(ln["count"] == 0 for ln in body["por_status"])


def test_relatorios_isolado_por_tenant(
    client: TestClient, seed_tenant: SeedTenant, no_cache: None
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    _seed_obras(owner_a.company_id)

    a = client.get("/api/v1/relatorios/obras-ativas", headers=owner_a.auth_header).json()
    b = client.get("/api/v1/relatorios/obras-ativas", headers=owner_b.auth_header).json()
    assert a["ativas"] == 2
    assert b["ativas"] == 0  # RLS: B não vê obras de A


# --------------------------------------------------------------------------- #
# Orçamentos
# --------------------------------------------------------------------------- #
def test_orcamentos_agrega_por_status(
    client: TestClient, seed_tenant: SeedTenant, no_cache: None
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _criar_obra(client, owner)
    _criar_orcamento(client, owner, obra_id, status=None)  # rascunho
    _criar_orcamento(client, owner, obra_id, status="aguardando_aprovacao")
    _criar_orcamento(client, owner, obra_id, status="aguardando_aprovacao")

    body = client.get("/api/v1/relatorios/orcamentos", headers=owner.auth_header).json()
    assert body["total"] == 3
    assert body["pendentes"] == 2
    por = {ln["status"]: ln for ln in body["por_status"]}
    assert [ln["status"] for ln in body["por_status"]] == [
        "rascunho",
        "em_revisao",
        "aguardando_aprovacao",
        "aprovado",
        "rejeitado",
    ]
    assert por["rascunho"]["count"] == 1
    assert por["aguardando_aprovacao"]["count"] == 2
    assert por["aprovado"]["count"] == 0


def test_orcamentos_vazio(client: TestClient, seed_tenant: SeedTenant, no_cache: None) -> None:
    owner = seed_tenant(role="owner")
    body = client.get("/api/v1/relatorios/orcamentos", headers=owner.auth_header).json()
    assert body["total"] == 0
    assert body["pendentes"] == 0
    assert Decimal(body["preco_venda_total"]) == Decimal("0.00")
    assert len(body["por_status"]) == 5


def test_orcamentos_pendentes_no_dashboard(client: TestClient, seed_tenant: SeedTenant) -> None:
    """B6.5 fecha o placeholder de B4.4: o KPI conta os aguardando aprovação."""
    from app.integrations.cache import get_dashboard_cache

    app.dependency_overrides[get_dashboard_cache] = NoopCache
    try:
        owner = seed_tenant(role="owner")
        obra_id = _criar_obra(client, owner)
        _criar_orcamento(client, owner, obra_id, status="aguardando_aprovacao")
        _criar_orcamento(client, owner, obra_id, status=None)  # rascunho, não conta

        body = client.get("/api/v1/dashboard/summary", headers=owner.auth_header).json()
        assert body["orcamentos_pendentes"] == 1
    finally:
        app.dependency_overrides.pop(get_dashboard_cache, None)
