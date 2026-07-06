"""Critério de aceite D1.2 (#4): com `app.company_id` setado para o tenant A,
uma SELECT sobre dados semeados de 2 empresas retorna apenas os da empresa A.

Conecta como `app_user` (role de runtime, sujeito a RLS — sem BYPASSRLS) para
validar o comportamento real que a TenantMiddleware vai depender no Estágio B.
"""

from __future__ import annotations

import uuid

import psycopg


def _select_as_tenant(conn: psycopg.Connection, company_id: str, sql: str) -> list[tuple]:
    with conn.transaction():
        with conn.cursor() as cur:
            # SET/SET LOCAL não aceita bind parameters; set_config() é a
            # forma parametrizável equivalente (3º argumento `true` = escopo
            # da transação atual, igual a SET LOCAL).
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(sql)
            return cur.fetchall()
    return []


def test_companies_isolation(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    rows_a = _select_as_tenant(
        app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM companies"
    )
    rows_b = _select_as_tenant(
        app_user_conn, two_tenants["B"]["company_id"], "SELECT id FROM companies"
    )

    ids_a = {str(r[0]) for r in rows_a}
    ids_b = {str(r[0]) for r in rows_b}

    assert ids_a == {two_tenants["A"]["company_id"]}
    assert ids_b == {two_tenants["B"]["company_id"]}
    assert ids_a.isdisjoint(ids_b)


def test_user_company_role_isolation(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    rows_a = _select_as_tenant(
        app_user_conn,
        two_tenants["A"]["company_id"],
        "SELECT user_id FROM user_company_role",
    )
    ids_a = {str(r[0]) for r in rows_a}

    assert ids_a == {two_tenants["A"]["user_id"]}
    assert two_tenants["B"]["user_id"] not in ids_a


def test_users_isolation_via_join(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    rows_a = _select_as_tenant(app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM users")
    ids_a = {str(r[0]) for r in rows_a}

    assert two_tenants["A"]["user_id"] in ids_a
    assert two_tenants["B"]["user_id"] not in ids_a


def test_no_tenant_set_returns_nothing(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    """Fail-closed: sem `app.company_id` setado, nenhuma linha é visível."""
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            cur.execute("SELECT id FROM companies")
            rows = cur.fetchall()
    assert rows == []


def test_unknown_company_id_returns_nothing(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    rows = _select_as_tenant(app_user_conn, str(uuid.uuid4()), "SELECT id FROM companies")
    assert rows == []
