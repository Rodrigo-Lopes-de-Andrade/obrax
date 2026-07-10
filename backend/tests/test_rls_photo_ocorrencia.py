"""B8.1 — isolamento multi-tenant (RLS) de photo e ocorrencia.

Mesma abordagem de test_rls_tickets: conecta como `app_user` (sujeito a RLS) e
valida que só as linhas do tenant A aparecem, que sem tenant é fail-closed, e
que INSERT cross-tenant é barrado pelo WITH CHECK.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def registros_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia cliente + obra + photo + ocorrencia em cada tenant (via `obrax`,
    bypassa RLS). Cleanup pelo teardown de `two_tenants` (cascade company_id)."""
    cpf_por_label = {"A": "52998224725", "B": "39053344705"}
    seeded: dict[str, dict[str, str]] = {}
    with SessionLocal() as session:
        for label, tenant in two_tenants.items():
            cid = tenant["company_id"]
            cliente_id = session.execute(
                text(
                    "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                    "VALUES (:cid, 'PF', :doc, :nome) RETURNING id"
                ),
                {"cid": cid, "doc": cpf_por_label[label], "nome": f"Cliente {label}"},
            ).scalar_one()
            obra_id = session.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, codigo, nome) "
                    "VALUES (:cid, :cliente_id, :codigo, :nome) RETURNING id"
                ),
                {
                    "cid": cid,
                    "cliente_id": cliente_id,
                    "codigo": f"OB-{label}",
                    "nome": f"Obra {label}",
                },
            ).scalar_one()
            photo_id = session.execute(
                text(
                    "INSERT INTO photo "
                    "(company_id, obra_id, client_photo_id, sha256, size_bytes, captured_at) "
                    "VALUES (:cid, :obra_id, :cpid, :sha, 1000, now()) RETURNING id"
                ),
                {"cid": cid, "obra_id": obra_id, "cpid": str(uuid.uuid4()), "sha": label * 64},
            ).scalar_one()
            ocorrencia_id = session.execute(
                text(
                    "INSERT INTO ocorrencia (company_id, obra_id, titulo) "
                    "VALUES (:cid, :obra_id, :titulo) RETURNING id"
                ),
                {"cid": cid, "obra_id": obra_id, "titulo": f"Ocorrência {label}"},
            ).scalar_one()
            seeded[label] = {
                "obra_id": str(obra_id),
                "photo_id": str(photo_id),
                "ocorrencia_id": str(ocorrencia_id),
            }
        session.commit()
    yield seeded


def _ids_as_tenant(conn: psycopg.Connection, company_id: str, sql: str) -> set[str]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(sql)
            return {str(r[0]) for r in cur.fetchall()}


def test_photo_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, registros_por_tenant: dict
) -> None:
    ids_a = _ids_as_tenant(app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM photo")
    assert ids_a == {registros_por_tenant["A"]["photo_id"]}
    assert registros_por_tenant["B"]["photo_id"] not in ids_a


def test_ocorrencia_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, registros_por_tenant: dict
) -> None:
    ids_a = _ids_as_tenant(
        app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM ocorrencia"
    )
    assert ids_a == {registros_por_tenant["A"]["ocorrencia_id"]}
    assert registros_por_tenant["B"]["ocorrencia_id"] not in ids_a


def test_fail_closed_sem_tenant(
    app_user_conn: psycopg.Connection, registros_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM photo")
            assert cur.fetchall() == []
            cur.execute("SELECT id FROM ocorrencia")
            assert cur.fetchall() == []


def test_insert_photo_cross_tenant_bloqueado(
    app_user_conn: psycopg.Connection, two_tenants: dict, registros_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO photo "
                    "(company_id, obra_id, client_photo_id, sha256, size_bytes, captured_at) "
                    "VALUES (%s, %s, %s, %s, 10, now())",
                    (
                        two_tenants["B"]["company_id"],
                        registros_por_tenant["B"]["obra_id"],
                        str(uuid.uuid4()),
                        "c" * 64,
                    ),
                )
