"""D3.2 — auditoria de documento via trigger (foco: mudança de visibilidade,
US-06). Lê `audit_log` pela role `obrax` (bypassa RLS) só para inspecionar o
que o trigger gravou — mesma abordagem de test_audit_log.py.
"""

from __future__ import annotations

import hashlib
import uuid
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
                    "SELECT table_name, action, before, after, actor_id "
                    "FROM audit_log WHERE record_id = :rid ORDER BY created_at, action"
                ),
                {"rid": record_id},
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    )
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-1", "nome": "Reforma"},
    )
    return str(resp.json()["id"])


def _create_doc(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    resp = client.post(
        f"/api/v1/obras/{obra_id}/documentos",
        headers=owner.auth_header,
        json={
            "nome": "planta.pdf",
            "tipo": "projeto",
            "sha256": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            "size_bytes": 10,
        },
    )
    assert resp.status_code == 201
    return str(resp.json()["documento_id"])


def test_audit_toggle_visibilidade(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)

    resp = client.patch(
        f"/api/v1/documentos/{doc_id}",
        headers=owner.auth_header,
        json={"visivel_cliente": True},
    )
    assert resp.status_code == 200

    rows = _audit_rows(doc_id)
    # POST (INSERT) + PATCH (UPDATE).
    assert [r["action"] for r in rows] == ["INSERT", "UPDATE"]
    update_row = rows[1]
    assert update_row["table_name"] == "documento"
    assert update_row["before"]["visivel_cliente"] is False
    assert update_row["after"]["visivel_cliente"] is True
    assert str(update_row["actor_id"]) == owner.user_id


def test_audit_soft_delete_documento(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    doc_id = _create_doc(client, owner, obra_id)

    assert (
        client.delete(f"/api/v1/documentos/{doc_id}", headers=owner.auth_header).status_code == 204
    )

    rows = _audit_rows(doc_id)
    # Soft delete é um UPDATE (deleted_at): INSERT + UPDATE.
    assert [r["action"] for r in rows] == ["INSERT", "UPDATE"]
    assert rows[1]["before"]["deleted_at"] is None
    assert rows[1]["after"]["deleted_at"] is not None
