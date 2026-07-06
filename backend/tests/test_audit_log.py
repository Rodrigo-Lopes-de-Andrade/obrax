"""B2.4 — audit_log via trigger (docs/SPRINTS.md: "Trigger audit_log on
INSERT/UPDATE/DELETE obras, clientes", "audit_log registra actor_id,
before/after JSONB, action enum, IP, created_at").

Lê `audit_log` direto pela role `obrax` (SessionLocal, bypassa RLS) — o
objetivo aqui é inspecionar o que o trigger gravou, não o isolamento.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _audit_rows(record_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = (
            session.execute(
                text(
                    "SELECT company_id, actor_id, table_name, record_id, action, "
                    "before, after, ip, created_at "
                    "FROM audit_log WHERE record_id = :rid ORDER BY created_at, action"
                ),
                {"rid": record_id},
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


def _criar_cliente(client: TestClient, owner: SeededUser, **extra_headers: str) -> dict[str, Any]:
    resp = client.post(
        "/api/v1/clientes",
        headers={**owner.auth_header, **extra_headers},
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Construtora X"},
    )
    assert resp.status_code == 201
    return resp.json()


def test_audit_insert_grava_actor_after_e_metadados(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    created = _criar_cliente(client, owner)

    rows = _audit_rows(created["id"])
    assert len(rows) == 1
    row = rows[0]
    assert row["action"] == "INSERT"
    assert row["table_name"] == "clientes"
    assert str(row["record_id"]) == created["id"]
    assert str(row["actor_id"]) == owner.user_id
    assert str(row["company_id"]) == owner.company_id
    assert row["before"] is None
    assert row["after"]["nome"] == "Construtora X"
    assert row["after"]["documento"] == "11222333000181"
    assert row["ip"] is None  # TestClient sem X-Forwarded-For → host inválido → NULL
    assert row["created_at"] is not None


def test_audit_update_registra_before_e_after(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    created = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Nome Antigo"},
    ).json()
    client.patch(
        f"/api/v1/clientes/{created['id']}",
        headers=owner.auth_header,
        json={"nome": "Nome Novo"},
    )

    rows = _audit_rows(created["id"])
    actions = [r["action"] for r in rows]
    assert actions == ["INSERT", "UPDATE"]
    update_row = rows[1]
    assert update_row["before"]["nome"] == "Nome Antigo"
    assert update_row["after"]["nome"] == "Nome Novo"
    assert str(update_row["actor_id"]) == owner.user_id


def test_audit_soft_delete_e_um_update_com_deleted_at(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    created = _criar_cliente(client, owner)
    assert (
        client.delete(f"/api/v1/clientes/{created['id']}", headers=owner.auth_header).status_code
        == 204
    )

    rows = _audit_rows(created["id"])
    # Soft delete é um UPDATE (deleted_at): INSERT + UPDATE.
    assert [r["action"] for r in rows] == ["INSERT", "UPDATE"]
    delete_row = rows[1]
    assert delete_row["before"]["deleted_at"] is None
    assert delete_row["after"]["deleted_at"] is not None


def test_audit_hard_delete_registra_action_delete(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    created = _criar_cliente(client, owner)
    # DELETE físico via obrax (bypassa RLS) — exercita o ramo DELETE do trigger.
    with SessionLocal() as session:
        session.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": created["id"]})
        session.commit()

    rows = _audit_rows(created["id"])
    assert [r["action"] for r in rows] == ["INSERT", "DELETE"]
    delete_row = rows[1]
    assert delete_row["before"]["nome"] == "Construtora X"
    assert delete_row["after"] is None


def test_audit_grava_obra(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente = _criar_cliente(client, owner)
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente["id"], "codigo": "OBR-1", "nome": "Reforma"},
    ).json()

    rows = _audit_rows(obra["id"])
    assert len(rows) == 1
    assert rows[0]["action"] == "INSERT"
    assert rows[0]["table_name"] == "obras"
    assert rows[0]["after"]["codigo"] == "OBR-1"


def test_audit_captura_ip_do_x_forwarded_for(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    created = _criar_cliente(client, owner, **{"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})

    rows = _audit_rows(created["id"])
    assert str(rows[0]["ip"]) == "203.0.113.7"
