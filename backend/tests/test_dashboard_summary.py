"""B4.4 — dashboard admin: KPIs agregados por tenant (US-01).

Contrato em docs/SPRINTS.md B4.4: obras ativas (count + valor total), tickets
abertos, orçamentos pendentes. Agregação isolada por company_id (RLS) e cache
de 60s. O cache é sobrescrito por `NoopCache` nos testes de conteúdo para
asserir sempre o estado atual do banco; o comportamento de cache tem teste
próprio (unit + endpoint stale).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.integrations.cache import InProcessTTLCache, NoopCache, get_dashboard_cache
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


@pytest.fixture
def no_cache() -> Iterator[None]:
    """Desliga o cache do dashboard para o teste ver o estado atual do banco."""
    app.dependency_overrides[get_dashboard_cache] = NoopCache
    yield
    app.dependency_overrides.pop(get_dashboard_cache, None)


def _seed_scenario(company_id: str, user_id: str) -> None:
    """2 obras ativas (execucao 1000 + planejamento 500), 2 inativas (concluida,
    cancelada) e 4 tickets (2 aberto, 1 andamento, 1 fechado) — via `obrax`
    (bypassa RLS). Esperado: ativas=2, valor=1500.00, tickets_abertos=2."""
    with SessionLocal() as session:
        cliente_id = session.execute(
            text(
                "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                "VALUES (:cid, 'PJ', :doc, 'Cliente') RETURNING id"
            ),
            {"cid": company_id, "doc": CNPJ_VALIDO},
        ).scalar_one()

        obra_a: str | None = None
        for codigo, status, valor in [
            ("A", "execucao", "1000.00"),
            ("B", "planejamento", "500.00"),
            ("C", "concluida", "9999.00"),
            ("D", "cancelada", "7777.00"),
        ]:
            oid = session.execute(
                text(
                    "INSERT INTO obras "
                    "(company_id, cliente_id, codigo, nome, status, valor_contrato) "
                    "VALUES (:cid, :cli, :cod, :nome, CAST(:st AS obra_status), :val) "
                    "RETURNING id"
                ),
                {
                    "cid": company_id,
                    "cli": cliente_id,
                    "cod": codigo,
                    "nome": f"Obra {codigo}",
                    "st": status,
                    "val": valor,
                },
            ).scalar_one()
            if codigo == "A":
                obra_a = str(oid)

        for st in ["aberto", "aberto", "andamento", "fechado"]:
            session.execute(
                text(
                    "INSERT INTO ticket (company_id, obra_id, titulo, status, created_by) "
                    "VALUES (:cid, :oid, 't', CAST(:st AS ticket_status), :uid)"
                ),
                {"cid": company_id, "oid": obra_a, "st": st, "uid": user_id},
            )
        session.commit()


def test_summary_zerado(client: TestClient, seed_tenant: SeedTenant, no_cache: None) -> None:
    owner = seed_tenant(role="owner")
    resp = client.get("/api/v1/dashboard/summary", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["obras_ativas"] == 0
    assert Decimal(str(body["obras_valor_total"])) == 0
    assert body["tickets_abertos"] == 0
    assert body["orcamentos_pendentes"] == 0


def test_summary_agrega(client: TestClient, seed_tenant: SeedTenant, no_cache: None) -> None:
    owner = seed_tenant(role="owner")
    _seed_scenario(owner.company_id, owner.user_id)
    body = client.get("/api/v1/dashboard/summary", headers=owner.auth_header).json()
    assert body["obras_ativas"] == 2
    assert Decimal(str(body["obras_valor_total"])) == Decimal("1500.00")
    assert body["tickets_abertos"] == 2
    assert body["orcamentos_pendentes"] == 0


def test_summary_isolado_por_tenant(
    client: TestClient, seed_tenant: SeedTenant, no_cache: None
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    _seed_scenario(owner_a.company_id, owner_a.user_id)

    a = client.get("/api/v1/dashboard/summary", headers=owner_a.auth_header).json()
    b = client.get("/api/v1/dashboard/summary", headers=owner_b.auth_header).json()
    assert a["obras_ativas"] == 2
    # Tenant B não enxerga nada de A (RLS).
    assert b["obras_ativas"] == 0
    assert Decimal(str(b["obras_valor_total"])) == 0
    assert b["tickets_abertos"] == 0


def test_cache_serve_valor_defasado(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Sem sobrescrever o cache (TTL real de 60s): a 1ª leitura cacheia os
    zeros; após semear dados, a 2ª leitura ainda devolve o valor cacheado —
    prova a janela de defasagem aceita."""
    owner = seed_tenant(role="owner")
    first = client.get("/api/v1/dashboard/summary", headers=owner.auth_header).json()
    assert first["obras_ativas"] == 0

    _seed_scenario(owner.company_id, owner.user_id)
    second = client.get("/api/v1/dashboard/summary", headers=owner.auth_header).json()
    # Servido do cache: ainda 0, apesar das obras recém-criadas.
    assert second["obras_ativas"] == 0


def test_ttl_cache_expira() -> None:
    """Unit do InProcessTTLCache com relógio injetado: hit dentro do TTL, miss
    depois de expirar."""
    now = {"t": 0.0}
    cache = InProcessTTLCache(ttl_seconds=60.0, clock=lambda: now["t"])
    cache.set("k", 42)
    assert cache.get("k") == 42
    now["t"] = 59.9
    assert cache.get("k") == 42
    now["t"] = 60.0
    assert cache.get("k") is None
