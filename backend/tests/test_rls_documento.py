"""B3.1 — isolamento multi-tenant (RLS) da tabela documento.

Mesma abordagem de `test_rls_clientes_obras.py`: conecta como `app_user`
(sujeito a RLS, sem BYPASSRLS) e valida que, com `app.company_id` no tenant A,
só os documentos de A aparecem — e que um INSERT cross-tenant é barrado pelo
`WITH CHECK` da policy. Fail-closed sem tenant.
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def documentos_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia 1 cliente + 1 obra + 1 documento em cada tenant (via `obrax`,
    bypassa RLS). O cleanup é feito pelo teardown de `two_tenants`: deletar a
    company cascateia para clientes/obras/documento (FK company_id CASCADE)."""
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
            documento_id = session.execute(
                text(
                    "INSERT INTO documento (company_id, obra_id, nome, tipo) "
                    "VALUES (:cid, :obra_id, :nome, 'projeto') RETURNING id"
                ),
                {"cid": cid, "obra_id": obra_id, "nome": f"planta-{label}.pdf"},
            ).scalar_one()
            seeded[label] = {"obra_id": str(obra_id), "documento_id": str(documento_id)}
        session.commit()
    yield seeded


def test_documento_isolation(
    app_user_conn: psycopg.Connection, two_tenants: dict, documentos_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.company_id', %s, true)",
                (two_tenants["A"]["company_id"],),
            )
            cur.execute("SELECT id FROM documento")
            ids_a = {str(r[0]) for r in cur.fetchall()}

    assert ids_a == {documentos_por_tenant["A"]["documento_id"]}
    assert documentos_por_tenant["B"]["documento_id"] not in ids_a


def test_documento_fail_closed_sem_tenant(
    app_user_conn: psycopg.Connection, documentos_por_tenant: dict
) -> None:
    """Sem `app.company_id` setado, nenhum documento é visível."""
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM documento")
            assert cur.fetchall() == []


def test_documento_insert_cross_tenant_bloqueado(
    app_user_conn: psycopg.Connection, two_tenants: dict, documentos_por_tenant: dict
) -> None:
    """Com contexto do tenant A, inserir um documento marcado como do tenant B
    (na obra de B) viola o `WITH CHECK` da policy → erro (RLS)."""
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO documento (company_id, obra_id, nome, tipo) "
                    "VALUES (%s, %s, 'intruso.pdf', 'outro')",
                    (two_tenants["B"]["company_id"], documentos_por_tenant["B"]["obra_id"]),
                )
