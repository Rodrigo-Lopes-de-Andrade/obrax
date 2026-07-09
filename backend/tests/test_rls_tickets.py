"""B4.1 — isolamento multi-tenant (RLS) de ticket e ticket_mensagem.

Mesma abordagem de test_rls_obra_membro: conecta como `app_user` (sujeito a
RLS) e valida que só as linhas do tenant A aparecem, e que INSERT cross-tenant
é barrado pelo WITH CHECK. Fail-closed sem tenant.
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def tickets_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia cliente + obra + ticket + 1 mensagem em cada tenant (via `obrax`,
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
            ticket_id = session.execute(
                text(
                    "INSERT INTO ticket (company_id, obra_id, titulo, created_by) "
                    "VALUES (:cid, :obra_id, :titulo, :uid) RETURNING id"
                ),
                {
                    "cid": cid,
                    "obra_id": obra_id,
                    "titulo": f"Chamado {label}",
                    "uid": tenant["user_id"],
                },
            ).scalar_one()
            msg_id = session.execute(
                text(
                    "INSERT INTO ticket_mensagem (company_id, ticket_id, author_id, content) "
                    "VALUES (:cid, :ticket_id, :uid, :content) RETURNING id"
                ),
                {
                    "cid": cid,
                    "ticket_id": ticket_id,
                    "uid": tenant["user_id"],
                    "content": f"msg {label}",
                },
            ).scalar_one()
            seeded[label] = {
                "obra_id": str(obra_id),
                "ticket_id": str(ticket_id),
                "msg_id": str(msg_id),
            }
        session.commit()
    yield seeded


def _ids_as_tenant(conn: psycopg.Connection, company_id: str, sql: str) -> set[str]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(sql)
            return {str(r[0]) for r in cur.fetchall()}


def test_ticket_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, tickets_por_tenant: dict
) -> None:
    ids_a = _ids_as_tenant(app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM ticket")
    assert ids_a == {tickets_por_tenant["A"]["ticket_id"]}
    assert tickets_por_tenant["B"]["ticket_id"] not in ids_a


def test_ticket_mensagem_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, tickets_por_tenant: dict
) -> None:
    ids_a = _ids_as_tenant(
        app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM ticket_mensagem"
    )
    assert ids_a == {tickets_por_tenant["A"]["msg_id"]}
    assert tickets_por_tenant["B"]["msg_id"] not in ids_a


def test_fail_closed_sem_tenant(
    app_user_conn: psycopg.Connection, tickets_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM ticket")
            assert cur.fetchall() == []
            cur.execute("SELECT id FROM ticket_mensagem")
            assert cur.fetchall() == []


def test_insert_ticket_cross_tenant_bloqueado(
    app_user_conn: psycopg.Connection, two_tenants: dict, tickets_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO ticket (company_id, obra_id, titulo) VALUES (%s, %s, 'intruso')",
                    (two_tenants["B"]["company_id"], tickets_por_tenant["B"]["obra_id"]),
                )
