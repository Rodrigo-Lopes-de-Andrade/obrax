"""B2.1 — isolamento multi-tenant (RLS) das tabelas clientes e obras.

Mesma abordagem de `test_rls_isolation.py`: conecta como `app_user` (sujeito a
RLS, sem BYPASSRLS) e valida que, com `app.company_id` setado para o tenant A,
só as linhas de A aparecem — e que um INSERT cross-tenant é barrado pelo
`WITH CHECK` da policy. Fail-closed sem tenant.
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def obras_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia 1 cliente + 1 obra em cada tenant (via `obrax`, bypassa RLS). O
    cleanup é feito pelo teardown de `two_tenants`: deletar a company cascateia
    para clientes/obras (FK company_id ON DELETE CASCADE)."""
    # CPFs válidos (dígito verificador) por tenant: desde 0012 há CHECK no banco
    # rejeitando documento inválido. O valor em si é irrelevante para o teste de
    # RLS — só precisa passar na validação.
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
            seeded[label] = {"cliente_id": str(cliente_id), "obra_id": str(obra_id)}
        session.commit()
    yield seeded


def _rows_as_tenant(conn: psycopg.Connection, company_id: str, sql: str) -> list[tuple]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(sql)
            return cur.fetchall()
    return []


def test_clientes_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, obras_por_tenant: dict
) -> None:
    rows_a = _rows_as_tenant(
        app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM clientes"
    )
    ids_a = {str(r[0]) for r in rows_a}

    assert ids_a == {obras_por_tenant["A"]["cliente_id"]}
    assert obras_por_tenant["B"]["cliente_id"] not in ids_a


def test_obras_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, obras_por_tenant: dict
) -> None:
    rows_a = _rows_as_tenant(app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM obras")
    ids_a = {str(r[0]) for r in rows_a}

    assert ids_a == {obras_por_tenant["A"]["obra_id"]}
    assert obras_por_tenant["B"]["obra_id"] not in ids_a


def test_fail_closed_sem_tenant(app_user_conn: psycopg.Connection, obras_por_tenant: dict) -> None:
    """Sem `app.company_id` setado, nenhuma linha de clientes/obras é visível."""
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM clientes")
            assert cur.fetchall() == []
            cur.execute("SELECT id FROM obras")
            assert cur.fetchall() == []


def test_insert_cross_tenant_bloqueado_por_with_check(
    app_user_conn: psycopg.Connection, two_tenants: dict
) -> None:
    """Com contexto do tenant A, inserir um cliente marcado como do tenant B
    viola o `WITH CHECK` da policy → erro (RLS)."""
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                # Documento válido de propósito: a única razão de falha deve ser
                # o WITH CHECK da RLS (não o CHECK de documento de 0012).
                cur.execute(
                    "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                    "VALUES (%s, 'PF', '46892787258', 'Intruso')",
                    (two_tenants["B"]["company_id"],),
                )
