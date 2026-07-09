"""B3.5 — isolamento multi-tenant (RLS) da tabela obra_membro.

Mesma abordagem de test_rls_documento: conecta como `app_user` (sujeito a RLS)
e valida que só os vínculos do tenant A aparecem, e que INSERT cross-tenant é
barrado pelo WITH CHECK. Fail-closed sem tenant.
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def membros_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia 1 cliente + 1 obra + 1 vínculo (o próprio owner) em cada tenant,
    via `obrax` (bypassa RLS). Cleanup pelo teardown de `two_tenants` (cascade
    company_id)."""
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
            membro_id = session.execute(
                text(
                    "INSERT INTO obra_membro (company_id, obra_id, user_id, papel) "
                    "VALUES (:cid, :obra_id, :user_id, 'mestre') RETURNING id"
                ),
                {"cid": cid, "obra_id": obra_id, "user_id": tenant["user_id"]},
            ).scalar_one()
            seeded[label] = {"obra_id": str(obra_id), "membro_id": str(membro_id)}
        session.commit()
    yield seeded


def test_obra_membro_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, membros_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.company_id', %s, true)",
                (two_tenants["A"]["company_id"],),
            )
            cur.execute("SELECT id FROM obra_membro")
            ids_a = {str(r[0]) for r in cur.fetchall()}

    assert ids_a == {membros_por_tenant["A"]["membro_id"]}
    assert membros_por_tenant["B"]["membro_id"] not in ids_a


def test_obra_membro_fail_closed_sem_tenant(
    app_user_conn: psycopg.Connection, membros_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM obra_membro")
            assert cur.fetchall() == []


def test_obra_membro_insert_cross_tenant_bloqueado(
    app_user_conn: psycopg.Connection, two_tenants: dict, membros_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO obra_membro (company_id, obra_id, user_id, papel) "
                    "VALUES (%s, %s, %s, 'intruso')",
                    (
                        two_tenants["B"]["company_id"],
                        membros_por_tenant["B"]["obra_id"],
                        two_tenants["B"]["user_id"],
                    ),
                )
