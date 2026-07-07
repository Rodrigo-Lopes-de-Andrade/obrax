"""D2.1 — validação de CPF/CNPJ no banco (constraint ck_clientes_documento_valido).

Insere direto como `app_user` (RLS ativa, contexto do tenant A) para exercitar a
CHECK independentemente da validação de API (validators.py): documento inválido
é barrado pela constraint (CheckViolation), válido passa.
"""

from __future__ import annotations

import psycopg
import pytest

CPF_VALIDO = "52998224725"
CNPJ_VALIDO = "11222333000181"


def _insert(conn: psycopg.Connection, company_id: str, tipo: str, doc: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
        cur.execute(
            "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
            "VALUES (%s, %s, %s, 'Teste')",
            (company_id, tipo, doc),
        )


def test_cpf_valido_insere(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    _insert(app_user_conn, two_tenants["A"]["company_id"], "PF", CPF_VALIDO)
    app_user_conn.rollback()  # não persiste — só prova que a CHECK aceitou


def test_cnpj_valido_insere(app_user_conn: psycopg.Connection, two_tenants: dict) -> None:
    _insert(app_user_conn, two_tenants["A"]["company_id"], "PJ", CNPJ_VALIDO)
    app_user_conn.rollback()


@pytest.mark.parametrize(
    "tipo,documento",
    [
        ("PF", "12345678900"),  # dígito verificador de CPF errado
        ("PF", "11111111111"),  # todos iguais
        ("PJ", "11222333000180"),  # dígito verificador de CNPJ errado
        ("PJ", CPF_VALIDO),  # 11 dígitos (CPF) num PJ → inválido como CNPJ
    ],
)
def test_documento_invalido_barrado_pela_check(
    app_user_conn: psycopg.Connection, two_tenants: dict, tipo: str, documento: str
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(app_user_conn, two_tenants["A"]["company_id"], tipo, documento)
    app_user_conn.rollback()
