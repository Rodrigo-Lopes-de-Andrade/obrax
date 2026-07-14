"""B11.5 — Isolamento multi-tenant (RLS) das tabelas do Módulo 3 (Agentes IA):
`ai_permission`, `agent_message`, `agent_interaction`.

Conecta como `app_user` (role de runtime, sujeita a RLS, sem BYPASSRLS) — o mesmo
comportamento real que a `TenantMiddleware`/`get_db` dependem em produção — e
valida três garantias por tabela:

1. Leitura isolada: com `app.company_id` = A, só linhas de A são visíveis.
2. Fail-closed: sem `app.company_id`, nenhuma linha é visível.
3. Escrita cross-tenant: a policy `WITH CHECK` barra INSERT de uma linha com
   `company_id` de outro tenant, mesmo autenticado como A.

Requer Postgres com as migrations aplicadas (roles `app_user`/`obrax`). Segue o
padrão de `test_rls_isolation.py` (set_config em escopo de transação).
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal

MODULO3_TABLES = ["ai_permission", "agent_message", "agent_interaction"]


@pytest.fixture
def seed_agentes(two_tenants: dict[str, dict[str, str]]) -> Iterator[dict[str, dict[str, str]]]:
    """Semeia 1 linha de cada tabela do Módulo 3 para os tenants A e B via role
    `obrax` (bypassa RLS). Retorna os ids por tenant/tabela. A limpeza explícita
    roda antes do teardown de `two_tenants` (que ainda cascatearia via companies).
    """
    ids: dict[str, dict[str, str]] = {"A": {}, "B": {}}
    with SessionLocal() as s:
        for label in ("A", "B"):
            cid = two_tenants[label]["company_id"]
            num = f"+5511{label.lower()}99990000"
            perm_id = s.execute(
                text(
                    "INSERT INTO ai_permission (company_id, whatsapp_number, role) "
                    "VALUES (:cid, :num, 'consultor') RETURNING id"
                ),
                {"cid": cid, "num": num},
            ).scalar_one()
            msg_id = s.execute(
                text(
                    "INSERT INTO agent_message (company_id, message_id, whatsapp_number, content) "
                    "VALUES (:cid, :mid, :num, 'qual o status da obra?') RETURNING id"
                ),
                {"cid": cid, "mid": f"wamid-{label}", "num": num},
            ).scalar_one()
            inter_id = s.execute(
                text(
                    "INSERT INTO agent_interaction (company_id, whatsapp_number, command) "
                    "VALUES (:cid, :num, 'status obra') RETURNING id"
                ),
                {"cid": cid, "num": num},
            ).scalar_one()
            ids[label] = {
                "ai_permission": str(perm_id),
                "agent_message": str(msg_id),
                "agent_interaction": str(inter_id),
            }
        s.commit()

    yield ids

    with SessionLocal() as s:
        for label in ("A", "B"):
            for table, row_id in ids[label].items():
                s.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})
        s.commit()


def _select_ids_as_tenant(conn: psycopg.Connection, company_id: str, table: str) -> set[str]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(f"SELECT id FROM {table}")
            return {str(r[0]) for r in cur.fetchall()}


@pytest.mark.parametrize("table", MODULO3_TABLES)
def test_modulo3_read_isolation(
    app_user_conn: psycopg.Connection,
    two_tenants: dict[str, dict[str, str]],
    seed_agentes: dict[str, dict[str, str]],
    table: str,
) -> None:
    """Com o tenant A no contexto, só a linha de A aparece; a de B nunca."""
    ids_a = _select_ids_as_tenant(app_user_conn, two_tenants["A"]["company_id"], table)
    assert seed_agentes["A"][table] in ids_a
    assert seed_agentes["B"][table] not in ids_a

    ids_b = _select_ids_as_tenant(app_user_conn, two_tenants["B"]["company_id"], table)
    assert ids_a.isdisjoint(ids_b)


@pytest.mark.parametrize("table", MODULO3_TABLES)
def test_modulo3_fail_closed(
    app_user_conn: psycopg.Connection,
    two_tenants: dict[str, dict[str, str]],
    seed_agentes: dict[str, dict[str, str]],
    table: str,
) -> None:
    """Sem `app.company_id` setado, RLS esconde tudo (fail-closed)."""
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {table}")
            assert cur.fetchall() == []


def test_ai_permission_cross_tenant_insert_denied(
    app_user_conn: psycopg.Connection,
    two_tenants: dict[str, dict[str, str]],
    seed_agentes: dict[str, dict[str, str]],
) -> None:
    """Autenticado como A, inserir uma linha com company_id de B viola a policy
    WITH CHECK — mesmo A não consegue plantar dado em outro tenant."""
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO ai_permission (company_id, whatsapp_number, role) "
                    "VALUES (%s, %s, 'consultor')",
                    (two_tenants["B"]["company_id"], "+5511900000000"),
                )
    app_user_conn.rollback()


def test_ai_permission_same_tenant_insert_allowed(
    app_user_conn: psycopg.Connection,
    two_tenants: dict[str, dict[str, str]],
    seed_agentes: dict[str, dict[str, str]],
) -> None:
    """Controle positivo: inserir com o próprio company_id passa na WITH CHECK.
    Faz rollback para não persistir a linha de teste."""
    cid_a = two_tenants["A"]["company_id"]
    try:
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (cid_a,))
            cur.execute(
                "INSERT INTO ai_permission (company_id, whatsapp_number, role) "
                "VALUES (%s, %s, 'consultor') RETURNING id",
                (cid_a, "+5511911110000"),
            )
            assert cur.fetchone() is not None
    finally:
        app_user_conn.rollback()
