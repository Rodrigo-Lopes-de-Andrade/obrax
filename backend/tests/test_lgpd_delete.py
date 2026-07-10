"""B9.5 / D9.1 — eliminação LGPD (right to be forgotten) + anonimização (US-21).

Cobre o fluxo do endpoint (soft-delete + pedido `pendente`) e as funções SQL de
anonimização: remoção do PII, tombstone em audit_log e a janela de 30 dias.
Clientes são semeados direto no banco (role `obrax`) para controlar `deleted_at`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.integrations.storage import ObjectStat, PresignedUpload, get_storage_client
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


class FakeStorage:
    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(url="x", method="PUT", expires_in=900)

    def stat(self, *, key: str) -> ObjectStat | None:
        return None

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        return None

    def get_object(self, *, key: str) -> bytes:
        return b""

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        return "x"


@pytest.fixture
def fake_storage() -> Iterator[FakeStorage]:
    storage = FakeStorage()
    app.dependency_overrides[get_storage_client] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_client, None)


def _seed_cliente(company_id: str, *, documento: str, deleted_days_ago: int | None = None) -> str:
    with SessionLocal() as s:
        cid = s.execute(
            text(
                "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome, email, telefone) "
                "VALUES (:c, 'PF', :doc, 'Fulano de Tal', 'fulano@example.com', '11999998888') "
                "RETURNING id"
            ),
            {"c": company_id, "doc": documento},
        ).scalar_one()
        if deleted_days_ago is not None:
            s.execute(
                text(
                    "UPDATE clientes SET deleted_at = now() - make_interval(days => :d) "
                    "WHERE id = :id"
                ),
                {"d": deleted_days_ago, "id": cid},
            )
        s.commit()
    return str(cid)


def test_delete_soft_deleta_e_registra_pendente(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(owner.company_id, documento="11144477735")

    resp = client.post(
        "/api/v1/lgpd/requests",
        headers=owner.auth_header,
        json={"request_type": "delete", "cliente_id": cliente_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["request_type"] == "delete"
    assert body["status"] == "pendente"
    assert body["cliente_id"] == cliente_id

    with SessionLocal() as s:
        row = s.execute(
            text("SELECT deleted_at, anonymized_at, nome FROM clientes WHERE id = :id"),
            {"id": cliente_id},
        ).mappings().one()
        assert row["deleted_at"] is not None  # soft-deletado
        assert row["anonymized_at"] is None  # PII ainda íntegro (anonimiza após 30d)
        assert row["nome"] == "Fulano de Tal"


def test_delete_exige_cliente_id_422(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/lgpd/requests", headers=owner.auth_header, json={"request_type": "delete"}
    )
    assert resp.status_code == 422


def test_delete_cliente_inexistente_404(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/lgpd/requests",
        headers=owner.auth_header,
        json={"request_type": "delete", "cliente_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


def test_anonimizar_cliente_remove_pii_e_audita(
    seed_tenant: SeedTenant,
) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(owner.company_id, documento="52998224725")

    with SessionLocal() as s:
        s.execute(text("SELECT lgpd_anonimizar_cliente(:id)"), {"id": cliente_id})
        s.commit()

    with SessionLocal() as s:
        row = s.execute(
            text(
                "SELECT documento, nome, email, telefone, anonymized_at "
                "FROM clientes WHERE id = :id"
            ),
            {"id": cliente_id},
        ).mappings().one()
        assert row["documento"].startswith("ANON-")
        assert row["nome"] == "[titular removido - LGPD]"
        assert row["email"] is None
        assert row["telefone"] is None
        assert row["anonymized_at"] is not None
        # Tombstone: o UPDATE de anonimização foi auditado (trigger de clientes).
        audits = s.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE table_name = 'clientes' AND action = 'UPDATE' AND record_id = :id"
            ),
            {"id": cliente_id},
        ).scalar_one()
        assert audits >= 1


def test_anonimizar_cliente_idempotente(seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(owner.company_id, documento="16899535009")
    with SessionLocal() as s:
        s.execute(text("SELECT lgpd_anonimizar_cliente(:id)"), {"id": cliente_id})
        s.commit()
        primeiro = s.execute(
            text("SELECT anonymized_at FROM clientes WHERE id = :id"), {"id": cliente_id}
        ).scalar_one()
        # Segunda chamada não re-processa (WHERE anonymized_at IS NULL).
        s.execute(text("SELECT lgpd_anonimizar_cliente(:id)"), {"id": cliente_id})
        s.commit()
        segundo = s.execute(
            text("SELECT anonymized_at FROM clientes WHERE id = :id"), {"id": cliente_id}
        ).scalar_one()
        assert primeiro == segundo


def test_anonimizar_expirados_respeita_janela_30d(seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    antigo = _seed_cliente(owner.company_id, documento="11144477735", deleted_days_ago=31)
    recente = _seed_cliente(owner.company_id, documento="52998224725", deleted_days_ago=5)

    with SessionLocal() as s:
        count = s.execute(text("SELECT lgpd_anonimizar_expirados()")).scalar_one()
        s.commit()
        assert count >= 1

        antigo_anon = s.execute(
            text("SELECT anonymized_at FROM clientes WHERE id = :id"), {"id": antigo}
        ).scalar_one()
        recente_anon = s.execute(
            text("SELECT anonymized_at FROM clientes WHERE id = :id"), {"id": recente}
        ).scalar_one()
        assert antigo_anon is not None  # >30 dias → anonimizado
        assert recente_anon is None  # dentro da janela → preservado
