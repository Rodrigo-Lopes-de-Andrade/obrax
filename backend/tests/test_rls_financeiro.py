"""S-F1 — isolamento multi-tenant (RLS) de `obra_fase` + verificação de schema.

Conecta como `app_user` (sujeito a RLS) com `app.company_id` setado. Inclui o
POSITIVO (A vê as próprias fases — sem ele, um schema onde ninguém vê nada passa
verde), negativos de leitura e de escrita (USING/WITH CHECK), UNIQUE
(obra_id, codigo) e a execução do `scripts/check_schema_financeiro.py`.

Fixtures inseridas direto via `obrax` (bypassa RLS), sem depender do service.
"""

from __future__ import annotations

import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.db import AppUserSessionLocal, SessionLocal

BACKEND = Path(__file__).resolve().parent.parent
CPF = {"A": "52998224725", "B": "39053344705"}


@pytest.fixture
def fases_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """1 cliente + 1 obra + 2 fases por tenant. Cleanup: o teardown de
    `two_tenants` deleta a company, que cascateia para tudo."""
    seeded: dict[str, dict[str, str]] = {}
    with SessionLocal() as s:
        for label, tenant in two_tenants.items():
            cid = tenant["company_id"]
            cliente_id = s.execute(
                text(
                    "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                    "VALUES (:cid, 'PF', :doc, :n) RETURNING id"
                ),
                {"cid": cid, "doc": CPF[label], "n": f"Cliente {label}"},
            ).scalar_one()
            obra_id = s.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, codigo, nome) "
                    "VALUES (:cid, :cl, :c, :n) RETURNING id"
                ),
                {"cid": cid, "cl": cliente_id, "c": f"OB-{label}", "n": f"Obra {label}"},
            ).scalar_one()
            fase_ids = []
            for i, (codigo, valor) in enumerate([("F001", "1000.50"), ("F002", "250.00")]):
                fase_ids.append(
                    str(
                        s.execute(
                            text(
                                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, "
                                "valor_orcado, sort_order) "
                                "VALUES (:cid, :o, :c, :d, :v, :so) RETURNING id"
                            ),
                            {
                                "cid": cid,
                                "o": obra_id,
                                "c": codigo,
                                "d": f"Fase {codigo} {label}",
                                "v": Decimal(valor),
                                "so": i,
                            },
                        ).scalar_one()
                    )
                )
            seeded[label] = {"obra_id": str(obra_id), "fase_ids": fase_ids}
        s.commit()
    yield seeded


def _ctx(cur: psycopg.Cursor, company_id: str) -> None:
    cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))


def _select(conn: psycopg.Connection, company_id: str, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.transaction(), conn.cursor() as cur:
        _ctx(cur, company_id)
        cur.execute(sql, params)
        return cur.fetchall()


def test_tenant_ve_as_proprias_fases(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """POSITIVO (SEC-F03): A enxerga exatamente as suas fases, com valores corretos."""
    rows = _select(
        app_user_conn,
        two_tenants["A"]["company_id"],
        "SELECT id, codigo, valor_orcado FROM obra_fase ORDER BY sort_order",
    )
    assert [str(r[0]) for r in rows] == fases_por_tenant["A"]["fase_ids"]
    assert [(r[1], r[2]) for r in rows] == [
        ("F001", Decimal("1000.50")),
        ("F002", Decimal("250.00")),
    ]


def test_tenant_nao_le_fases_de_outro(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """SEC-F02, leitura: A recebe zero linhas das fases de B, por id e por obra."""
    for sql, params in (
        ("SELECT id FROM obra_fase WHERE obra_id = %s", (fases_por_tenant["B"]["obra_id"],)),
        (
            "SELECT id FROM obra_fase WHERE id = ANY(%s::uuid[])",
            (fases_por_tenant["B"]["fase_ids"],),
        ),
    ):
        assert _select(app_user_conn, two_tenants["A"]["company_id"], sql, params) == []
    todos = {
        str(r[0])
        for r in _select(app_user_conn, two_tenants["A"]["company_id"], "SELECT id FROM obra_fase")
    }
    assert todos.isdisjoint(fases_por_tenant["B"]["fase_ids"])


def test_sem_contexto_ou_contexto_vazio_nega_limpo(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """app_current_company_id(): contexto vazio dá zero linhas, não erro de cast."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        cur.execute("SELECT id FROM obra_fase")
        assert cur.fetchall() == []
    assert _select(app_user_conn, "", "SELECT id FROM obra_fase") == []
    assert _select(app_user_conn, str(uuid.uuid4()), "SELECT id FROM obra_fase") == []


def test_tenant_nao_altera_nem_apaga_fases_de_outro(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """SEC-F02, escrita: UPDATE/DELETE em linha de B afeta zero linhas e nada muda."""
    fase_b = fases_por_tenant["B"]["fase_ids"][0]
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute("UPDATE obra_fase SET descricao = 'invadido' WHERE id = %s", (fase_b,))
        assert cur.rowcount == 0
        cur.execute("DELETE FROM obra_fase WHERE id = %s", (fase_b,))
        assert cur.rowcount == 0
    with SessionLocal() as s:
        desc = s.execute(
            text("SELECT descricao FROM obra_fase WHERE id = :i"), {"i": fase_b}
        ).scalar_one()
    assert desc == "Fase F001 B"


def test_tenant_nao_insere_com_company_id_de_outro(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """WITH CHECK: A não grava fase com company_id de B (nem na obra de B)."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with app_user_conn.transaction(), app_user_conn.cursor() as cur:
            _ctx(cur, two_tenants["A"]["company_id"])
            cur.execute(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
                "VALUES (%s, %s, 'F999', 'x', 1, 9)",
                (two_tenants["B"]["company_id"], fases_por_tenant["B"]["obra_id"]),
            )


def test_tenant_nao_move_fase_propria_para_outro_tenant(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """WITH CHECK no UPDATE: A não reatribui fase sua ao company_id de B."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with app_user_conn.transaction(), app_user_conn.cursor() as cur:
            _ctx(cur, two_tenants["A"]["company_id"])
            cur.execute(
                "UPDATE obra_fase SET company_id = %s WHERE id = %s",
                (two_tenants["B"]["company_id"], fases_por_tenant["A"]["fase_ids"][0]),
            )


def test_tenant_insere_fase_propria(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """Contraprova do WITH CHECK: a escrita legítima no próprio tenant passa."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
            "VALUES (%s, %s, 'F003', 'nova', 10.00, 2) RETURNING ativa",
            (two_tenants["A"]["company_id"], fases_por_tenant["A"]["obra_id"]),
        )
        assert cur.fetchone() == (True,)
        cur.execute("SELECT count(*) FROM obra_fase")
        assert cur.fetchone() == (3,)
    app_user_conn.rollback()


def test_unique_obra_codigo_rejeita_duplicata(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        with app_user_conn.transaction(), app_user_conn.cursor() as cur:
            _ctx(cur, two_tenants["A"]["company_id"])
            cur.execute(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
                "VALUES (%s, %s, 'F001', 'dup', 1, 5)",
                (two_tenants["A"]["company_id"], fases_por_tenant["A"]["obra_id"]),
            )


def test_valor_orcado_negativo_recusado(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        with app_user_conn.transaction(), app_user_conn.cursor() as cur:
            _ctx(cur, two_tenants["A"]["company_id"])
            cur.execute(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
                "VALUES (%s, %s, 'F009', 'neg', -1, 5)",
                (two_tenants["A"]["company_id"], fases_por_tenant["A"]["obra_id"]),
            )


def test_policy_usa_app_current_company_id() -> None:
    """Catálogo: o predicado da policy chama o helper, não o cast cru."""
    with SessionLocal() as s:
        rows = s.execute(
            text(
                "SELECT pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid) "
                "FROM pg_policy WHERE polrelid = 'obra_fase'::regclass"
            )
        ).all()
    assert rows, "obra_fase sem policy"
    for using, check in rows:
        assert using == "(company_id = app_current_company_id())"
        assert check == "(company_id = app_current_company_id())"


def test_check_schema_financeiro_script_passa() -> None:
    r = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / "check_schema_financeiro.py")],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "obra_fase" in r.stdout


def _erros_com_sentinela(
    *ddl: str, policy_using: str = "company_id = app_current_company_id()"
) -> str:
    """Cria `obra_fase_sentinela` (RLS enabled+forced, policy, GRANTs padrão) numa
    transação, aplica `ddl`, roda `verificar()` e reverte. Devolve as falhas."""
    from scripts import check_schema_financeiro as chk

    from app.core.config import settings

    with psycopg.connect(settings.database_url_raw) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE obra_fase_sentinela (id int, company_id uuid)")
                cur.execute("ALTER TABLE obra_fase_sentinela ENABLE ROW LEVEL SECURITY")
                cur.execute("ALTER TABLE obra_fase_sentinela FORCE ROW LEVEL SECURITY")
                cur.execute(
                    f"CREATE POLICY p ON obra_fase_sentinela FOR ALL "
                    f"USING ({policy_using}) WITH CHECK ({policy_using})"
                )
                cur.execute(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON obra_fase_sentinela "
                    "TO app_user, app_admin"
                )
                for stmt in ddl:
                    cur.execute(stmt)
            original = chk.TABELAS_MODULO
            chk.TABELAS_MODULO = (*original, "obra_fase_sentinela")
            try:
                erros = chk.verificar(conn)
            finally:
                chk.TABELAS_MODULO = original
        finally:
            conn.rollback()
    return "\n".join(e for e in erros if e.startswith("obra_fase_sentinela"))


def test_check_schema_sentinela_integra_passa() -> None:
    """Controle: a sentinela sem mutação não gera nenhuma falha."""
    assert _erros_com_sentinela() == ""


def test_check_schema_detecta_falhas() -> None:
    """O verificador falha de verdade: tabela temporária sem FORCE/WITH CHECK/GRANT
    é reportada. (Roda numa transação revertida, só com `verificar()`.)"""
    from scripts import check_schema_financeiro as chk

    from app.core.config import settings

    with psycopg.connect(settings.database_url_raw) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE obra_fase_sentinela (id int, company_id uuid)")
            cur.execute("ALTER TABLE obra_fase_sentinela ENABLE ROW LEVEL SECURITY")
            cur.execute(
                "CREATE POLICY p ON obra_fase_sentinela FOR SELECT "
                "USING (company_id = app_current_company_id())"
            )
            cur.execute("REVOKE ALL ON obra_fase_sentinela FROM app_user")
        original = chk.TABELAS_MODULO
        chk.TABELAS_MODULO = (*original, "obra_fase_sentinela")
        try:
            erros = chk.verificar(conn)
        finally:
            chk.TABELAS_MODULO = original
        conn.rollback()
    texto = "\n".join(erros)
    assert "obra_fase_sentinela: RLS não está habilitada E forçada" in texto
    assert "sem WITH CHECK" in texto
    for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        assert f"obra_fase_sentinela: falta GRANT {priv} para app_user" in texto


@pytest.mark.parametrize("role", ["app_user", "app_admin"])
@pytest.mark.parametrize("priv", ["SELECT", "INSERT", "UPDATE", "DELETE"])
def test_check_schema_detecta_revogacao_parcial(role: str, priv: str) -> None:
    """R1: revogar UM privilégio de UM role basta para falhar, e só ele é citado."""
    texto = _erros_com_sentinela(f"REVOKE {priv} ON obra_fase_sentinela FROM {role}")
    assert texto == f"obra_fase_sentinela: falta GRANT {priv} para {role}"


def test_check_schema_detecta_policy_com_cast_cru() -> None:
    """O1: policy com `current_setting(...)::uuid` em vez do helper é reprovada."""
    texto = _erros_com_sentinela(
        policy_using="company_id = (current_setting('app.company_id'))::uuid"
    )
    assert "policy p (USING) fora do padrão" in texto
    assert "policy p (WITH CHECK) fora do padrão" in texto
    assert "current_setting" in texto  # a expressão encontrada é mostrada


def test_check_schema_detecta_policy_com_or_true() -> None:
    """O3: `... OR true` contém o helper e não contém current_setting (passava na
    checagem por substring), mas a comparação exata o reprova mostrando a expressão."""
    texto = _erros_com_sentinela(policy_using="company_id = app_current_company_id() OR true")
    assert "policy p (USING) fora do padrão" in texto
    assert "policy p (WITH CHECK) fora do padrão" in texto
    assert "OR true" in texto
    assert "(company_id = app_current_company_id())" in texto  # esperado


# --------------------------------------------------------------------------
# O4 — oráculo cross-tenant (ESPEC §7.5) e lock que não vaza entre tenants
# --------------------------------------------------------------------------

SENTINELA = "TITULO-SENTINELA-SECRETO-A"


def _app_session(company_id: str) -> Session:
    """Sessão `app_user` (RLS) com o GUC do tenant, local à transação."""
    s = AppUserSessionLocal()
    try:
        s.execute(text("SELECT set_config('app.company_id', :c, true)"), {"c": company_id})
        assert s.execute(text("SELECT current_user")).scalar_one() == "app_user"
    except BaseException:
        s.close()
        raise
    return s


@pytest.fixture
def orcamentos_de_a(two_tenants: dict, fases_por_tenant: dict) -> dict[str, str]:
    """Tenant A: obra com 2 orçamentos (v1 cada): o 1º aprovado (título sentinela),
    o 2º rascunho. Teardown: cascata da company em `two_tenants`."""
    cid = two_tenants["A"]["company_id"]
    obra_id = fases_por_tenant["A"]["obra_id"]
    ids: dict[str, str] = {}
    with SessionLocal() as s:
        for chave, titulo, status in (
            ("aprovado", SENTINELA, "aprovado"),
            ("segundo", "Segundo orcamento A", "rascunho"),
        ):
            oid = s.execute(
                text(
                    "INSERT INTO orcamento (company_id, obra_id, titulo, status) "
                    "VALUES (:c, :o, :t, CAST(:s AS orcamento_status)) RETURNING id"
                ),
                {"c": cid, "o": obra_id, "t": titulo, "s": status},
            ).scalar_one()
            s.execute(
                text(
                    "INSERT INTO orcamento_versao (company_id, orcamento_id, numero) "
                    "VALUES (:c, :o, 1)"
                ),
                {"c": cid, "o": oid},
            )
            ids[chave] = str(oid)
        s.commit()
    ids["obra_id"] = obra_id
    return ids


def test_oraculo_cross_tenant_nao_vaza_titulo(
    two_tenants: dict, orcamentos_de_a: dict[str, str]
) -> None:
    """ESPEC §7.5: com o GUC de B, o id de orçamento de A é 404 genérico — nunca o 409
    que citaria o título do outro orçamento aprovado. Contraprova com o GUC de A."""
    from app.modules.financeiro.services.fases import sincronizar_fases, validar_aprovacao

    for funcao in (validar_aprovacao, sincronizar_fases):
        s = _app_session(two_tenants["B"]["company_id"])
        try:
            with pytest.raises(HTTPException) as exc:
                funcao(s, uuid.UUID(orcamentos_de_a["segundo"]))
            assert exc.value.status_code == 404
            assert exc.value.detail == "orçamento não encontrado"
            assert SENTINELA not in str(exc.value.detail)
        finally:
            s.rollback()
            s.close()

    # Contraprova: no tenant dono a checagem funciona e cita o título.
    s = _app_session(two_tenants["A"]["company_id"])
    try:
        with pytest.raises(HTTPException) as exc:
            validar_aprovacao(s, uuid.UUID(orcamentos_de_a["segundo"]))
        assert exc.value.status_code == 409
        assert SENTINELA in str(exc.value.detail)
    finally:
        s.rollback()
        s.close()


_TRAVA = "SELECT id FROM obras WHERE id = :o FOR NO KEY UPDATE"


def test_lock_de_obra_nao_vaza_entre_tenants(two_tenants: dict, fases_por_tenant: dict) -> None:
    """Sessão 1 (A) segura o lock; B não enxerga a linha (0 linhas, sem bloquear);
    controle: outra sessão de A bloqueia e estoura lock_timeout."""
    obra_a = {"o": fases_por_tenant["A"]["obra_id"]}
    s1 = s2 = s3 = None
    try:
        s1 = _app_session(two_tenants["A"]["company_id"])
        assert len(s1.execute(text(_TRAVA), obra_a).all()) == 1  # segura

        s2 = _app_session(two_tenants["B"]["company_id"])
        s2.execute(text("SET LOCAL lock_timeout = '2s'"))
        t0 = time.monotonic()
        assert s2.execute(text(_TRAVA), obra_a).all() == []
        assert time.monotonic() - t0 < 1.5, "B esperou por lock de A (vazamento)"

        s3 = _app_session(two_tenants["A"]["company_id"])
        s3.execute(text("SET LOCAL lock_timeout = '1s'"))
        with pytest.raises(OperationalError) as exc:
            s3.execute(text(_TRAVA), obra_a)
        assert isinstance(exc.value.orig, psycopg.errors.LockNotAvailable)
    finally:
        for s in (s3, s2, s1):
            if s is not None:
                s.rollback()
                s.close()


# --------------------------------------------------------------------------
# S-F3 — categoria_financeira e despesa: RLS, CHECKs e FK composta (E-08)
# --------------------------------------------------------------------------

_INS_DESPESA = (
    "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, fornecedor_nome, "
    "descricao, valor, data_competencia, vencimento, status, data_pagamento) "
    "VALUES (%s, %s, %s, %s, 'Forn', 'desc', %s, '2026-11-01', '2026-11-30', "
    "%s::despesa_status, %s)"
)


@pytest.fixture
def despesas_por_tenant(two_tenants: dict, fases_por_tenant: dict) -> dict[str, dict[str, str]]:
    """1 categoria + 1 despesa (prevista, 100.50) por tenant, inseridas via `obrax`.
    Cleanup: cascata da company em `two_tenants`."""
    out: dict[str, dict[str, str]] = {}
    with SessionLocal() as s:
        for label, tenant in two_tenants.items():
            cid = tenant["company_id"]
            cat = s.execute(
                text(
                    "INSERT INTO categoria_financeira (company_id, nome) "
                    "VALUES (:c, :n) RETURNING id"
                ),
                {"c": cid, "n": f"Material {label}"},
            ).scalar_one()
            desp = s.execute(
                text(
                    "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, "
                    "fornecedor_nome, descricao, valor, data_competencia, vencimento, status) "
                    "VALUES (:c, :o, :f, :cat, 'Forn', :d, :v, '2026-11-01', '2026-11-30', "
                    "'prevista') RETURNING id"
                ),
                {
                    "c": cid,
                    "o": fases_por_tenant[label]["obra_id"],
                    "f": fases_por_tenant[label]["fase_ids"][0],
                    "cat": cat,
                    "d": f"Despesa {label}",
                    "v": Decimal("100.50"),
                },
            ).scalar_one()
            out[label] = {"categoria_id": str(cat), "despesa_id": str(desp)}
        s.commit()
    return out


def _exec_as(conn: psycopg.Connection, company_id: str, sql: str, params: tuple = ()) -> None:
    """Executa uma escrita como app_user com a GUC dada; a transação é revertida
    (o erro, se houver, sobe para o chamador)."""
    try:
        with conn.transaction(), conn.cursor() as cur:
            _ctx(cur, company_id)
            cur.execute(sql, params)
            raise _Rollback
    except _Rollback:
        pass


class _Rollback(Exception):
    pass


def test_tenant_ve_as_proprias_categorias_e_despesas(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    """POSITIVO: A vê a própria categoria e a própria despesa, com valor exato."""
    cid = two_tenants["A"]["company_id"]
    cats = _select(app_user_conn, cid, "SELECT id, nome FROM categoria_financeira")
    assert [(str(r[0]), r[1]) for r in cats] == [
        (despesas_por_tenant["A"]["categoria_id"], "Material A")
    ]
    desp = _select(app_user_conn, cid, "SELECT id, valor, status FROM despesa")
    assert [(str(r[0]), r[1], r[2]) for r in desp] == [
        (despesas_por_tenant["A"]["despesa_id"], Decimal("100.50"), "prevista")
    ]


def test_tenant_nao_le_categorias_nem_despesas_de_outro(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    """NEGATIVO, leitura: A recebe zero linhas de B, por id e na listagem geral."""
    cid = two_tenants["A"]["company_id"]
    b = despesas_por_tenant["B"]
    assert (
        _select(
            app_user_conn,
            cid,
            "SELECT id FROM categoria_financeira WHERE id = %s",
            (b["categoria_id"],),
        )
        == []
    )
    assert (
        _select(app_user_conn, cid, "SELECT id FROM despesa WHERE id = %s", (b["despesa_id"],))
        == []
    )
    assert b["categoria_id"] not in {
        str(r[0]) for r in _select(app_user_conn, cid, "SELECT id FROM categoria_financeira")
    }
    assert b["despesa_id"] not in {
        str(r[0]) for r in _select(app_user_conn, cid, "SELECT id FROM despesa")
    }
    # contexto vazio / inexistente: negação limpa
    for tabela in ("categoria_financeira", "despesa"):
        assert _select(app_user_conn, "", f"SELECT id FROM {tabela}") == []
        assert _select(app_user_conn, str(uuid.uuid4()), f"SELECT id FROM {tabela}") == []


def test_tenant_nao_altera_nem_apaga_categoria_e_despesa_de_outro(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    """NEGATIVO, escrita: UPDATE/DELETE em linha de B afeta zero linhas e nada muda."""
    b = despesas_por_tenant["B"]
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            "UPDATE categoria_financeira SET nome = 'invadida' WHERE id = %s", (b["categoria_id"],)
        )
        assert cur.rowcount == 0
        cur.execute("DELETE FROM categoria_financeira WHERE id = %s", (b["categoria_id"],))
        assert cur.rowcount == 0
        cur.execute("UPDATE despesa SET descricao = 'invadida' WHERE id = %s", (b["despesa_id"],))
        assert cur.rowcount == 0
        cur.execute("DELETE FROM despesa WHERE id = %s", (b["despesa_id"],))
        assert cur.rowcount == 0
    with SessionLocal() as s:
        nome = s.execute(
            text("SELECT nome FROM categoria_financeira WHERE id = :i"), {"i": b["categoria_id"]}
        ).scalar_one()
        desc = s.execute(
            text("SELECT descricao FROM despesa WHERE id = :i"), {"i": b["despesa_id"]}
        ).scalar_one()
    assert (nome, desc) == ("Material B", "Despesa B")


def test_tenant_nao_insere_categoria_nem_despesa_com_company_id_de_outro(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
) -> None:
    """WITH CHECK: A não grava categoria/despesa com company_id de B (policy, não FK)."""
    a, b = two_tenants["A"]["company_id"], two_tenants["B"]["company_id"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _exec_as(
            app_user_conn,
            a,
            "INSERT INTO categoria_financeira (company_id, nome) VALUES (%s, 'x')",
            (b,),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _exec_as(
            app_user_conn,
            a,
            _INS_DESPESA,
            (
                b,
                fases_por_tenant["B"]["obra_id"],
                fases_por_tenant["B"]["fase_ids"][0],
                despesas_por_tenant["B"]["categoria_id"],
                Decimal("1.00"),
                "prevista",
                None,
            ),
        )


# ---- E-08: FK composta, medida como app_user com a GUC de A ----------------


def _despesa_params(
    two_tenants: dict, fases: dict, desp: dict, *, obra: str, fase: str, categoria: str
) -> tuple:
    return (
        two_tenants["A"]["company_id"],
        fases[obra]["obra_id"],
        fases[fase]["fase_ids"][0],
        desp[categoria]["categoria_id"],
        Decimal("10.00"),
        "prevista",
        None,
    )


@pytest.mark.parametrize(
    ("obra", "fase", "categoria"),
    [("B", "A", "A"), ("A", "B", "A"), ("A", "A", "B")],
    ids=["obra_de_B", "fase_de_B", "categoria_de_B"],
)
def test_e08_despesa_de_a_apontando_para_b_falha_por_fk(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    obra: str,
    fase: str,
    categoria: str,
) -> None:
    """company_id = A com obra, fase ou categoria de B: ForeignKeyViolation (e não
    InsufficientPrivilege: a policy aceita, quem barra é a FK composta)."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _exec_as(
            app_user_conn,
            two_tenants["A"]["company_id"],
            _INS_DESPESA,
            _despesa_params(
                two_tenants,
                fases_por_tenant,
                despesas_por_tenant,
                obra=obra,
                fase=fase,
                categoria=categoria,
            ),
        )


def test_e08_despesa_de_a_apontando_para_a_passa(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
) -> None:
    """Positivo: o mesmo INSERT, com obra, fase e categoria de A, passa."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            _INS_DESPESA + " RETURNING status",
            _despesa_params(
                two_tenants,
                fases_por_tenant,
                despesas_por_tenant,
                obra="A",
                fase="A",
                categoria="A",
            ),
        )
        assert cur.fetchone() == ("prevista",)
        cur.execute("SELECT count(*) FROM despesa")
        assert cur.fetchone() == (2,)
    app_user_conn.rollback()


def test_e08_obra_fase_de_a_apontando_para_obra_de_b_falha_por_fk(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """obra_fase com company_id = A e obra de B: ForeignKeyViolation."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _exec_as(
            app_user_conn,
            two_tenants["A"]["company_id"],
            "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
            "VALUES (%s, %s, 'F900', 'x', 1, 9)",
            (two_tenants["A"]["company_id"], fases_por_tenant["B"]["obra_id"]),
        )


def test_e08_obra_fase_de_a_apontando_para_obra_de_a_passa(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """Positivo: o mesmo INSERT, com a obra de A, passa."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
            "VALUES (%s, %s, 'F900', 'x', 1, 9) RETURNING codigo",
            (two_tenants["A"]["company_id"], fases_por_tenant["A"]["obra_id"]),
        )
        assert cur.fetchone() == ("F900",)
    app_user_conn.rollback()


def test_e08_codigo_de_fase_de_outra_empresa_nao_e_oraculo(
    app_user_conn: psycopg.Connection, two_tenants: dict, fases_por_tenant: dict
) -> None:
    """B tem a fase 'F001' na obra de B. A, tentando 'F001' na obra de B, recebe o
    MESMO erro (FK) que receberia com um código inexistente: nunca UniqueViolation,
    que revelaria que a obra de B existe e já tem esse código."""
    sql = (
        "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, sort_order) "
        "VALUES (%s, %s, %s, 'x', 1, 9)"
    )
    a = two_tenants["A"]["company_id"]
    obra_b = fases_por_tenant["B"]["obra_id"]
    for codigo in ("F001", "NAO-EXISTE"):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _exec_as(app_user_conn, a, sql, (a, obra_b, codigo))


def test_e08_unique_de_codigo_inclui_company_id() -> None:
    """Catálogo: a unicidade do código de fase é (company_id, obra_id, codigo)."""
    with SessionLocal() as s:
        defs = (
            s.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'obra_fase'::regclass AND contype = 'u'"
                )
            )
            .scalars()
            .all()
        )
    assert "UNIQUE (company_id, obra_id, codigo)" in defs
    assert "UNIQUE (obra_id, codigo)" not in defs


# ---- CHECKs da despesa (nível do banco) ------------------------------------


def _inserir_despesa(
    conn, two_tenants, fases, desp, *, valor="10.00", status, data_pagamento
) -> None:
    _exec_as(
        conn,
        two_tenants["A"]["company_id"],
        _INS_DESPESA,
        (
            two_tenants["A"]["company_id"],
            fases["A"]["obra_id"],
            fases["A"]["fase_ids"][0],
            desp["A"]["categoria_id"],
            Decimal(valor),
            status,
            data_pagamento,
        ),
    )


@pytest.mark.parametrize(
    ("status", "data_pagamento"),
    [("paga", None), ("prevista", "2026-11-10"), ("cancelada", "2026-11-10")],
    ids=["paga_sem_data", "prevista_com_data", "cancelada_com_data"],
)
def test_check_pago_exige_data_e_data_exige_pago(
    app_user_conn, two_tenants, fases_por_tenant, despesas_por_tenant, status, data_pagamento
) -> None:
    """Os dois estados mentirosos simétricos são rejeitados pelo CHECK."""
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        _inserir_despesa(
            app_user_conn,
            two_tenants,
            fases_por_tenant,
            despesas_por_tenant,
            status=status,
            data_pagamento=data_pagamento,
        )
    assert exc.value.diag.constraint_name == "ck_despesa_pago_com_data"


@pytest.mark.parametrize(
    ("status", "data_pagamento"),
    [("paga", "2026-11-10"), ("prevista", None), ("cancelada", None)],
    ids=["paga_com_data", "prevista_sem_data", "cancelada_sem_data"],
)
def test_check_pago_aceita_estados_coerentes(
    app_user_conn, two_tenants, fases_por_tenant, despesas_por_tenant, status, data_pagamento
) -> None:
    """Contraprova: os estados coerentes passam (sem exceção)."""
    _inserir_despesa(
        app_user_conn,
        two_tenants,
        fases_por_tenant,
        despesas_por_tenant,
        status=status,
        data_pagamento=data_pagamento,
    )


@pytest.mark.parametrize("valor", ["0.00", "-1.00"])
def test_check_valor_positivo(
    app_user_conn, two_tenants, fases_por_tenant, despesas_por_tenant, valor
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        _inserir_despesa(
            app_user_conn,
            two_tenants,
            fases_por_tenant,
            despesas_por_tenant,
            valor=valor,
            status="prevista",
            data_pagamento=None,
        )
    assert exc.value.diag.constraint_name == "ck_despesa_valor_positivo"


def test_check_pagar_via_update_exige_data(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    """UPDATE para 'paga' sem data é recusado; com data passa."""
    cid, did = two_tenants["A"]["company_id"], despesas_por_tenant["A"]["despesa_id"]
    with pytest.raises(psycopg.errors.CheckViolation):
        _exec_as(app_user_conn, cid, "UPDATE despesa SET status = 'paga' WHERE id = %s", (did,))
    _exec_as(
        app_user_conn,
        cid,
        "UPDATE despesa SET status = 'paga', data_pagamento = '2026-11-10' WHERE id = %s",
        (did,),
    )


# ---- Categoria: FK impede excluir; unicidade e seed idempotente ------------


def test_categoria_com_despesa_nao_e_excluivel_so_desativavel(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    cid, cat = two_tenants["A"]["company_id"], despesas_por_tenant["A"]["categoria_id"]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _exec_as(app_user_conn, cid, "DELETE FROM categoria_financeira WHERE id = %s", (cat,))
    # desativar é permitido, e a categoria continua visível (relatórios históricos)
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, cid)
        cur.execute("UPDATE categoria_financeira SET ativa = false WHERE id = %s", (cat,))
        assert cur.rowcount == 1
        cur.execute("SELECT ativa FROM categoria_financeira WHERE id = %s", (cat,))
        assert cur.fetchone() == (False,)
    app_user_conn.rollback()


def test_categoria_unica_por_empresa_sem_caixa_e_ignora_soft_delete(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    cid = two_tenants["A"]["company_id"]
    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        _exec_as(
            app_user_conn,
            cid,
            "INSERT INTO categoria_financeira (company_id, nome) VALUES (%s, 'MATERIAL a')",
            (cid,),
        )
    assert exc.value.diag.constraint_name == "uq_categoria_company_nome"
    # o mesmo nome em OUTRA empresa é livre; e nome de categoria soft-deletada é reutilizável
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, cid)
        cur.execute("UPDATE categoria_financeira SET deleted_at = now() WHERE nome = 'Material A'")
        cur.execute(
            "INSERT INTO categoria_financeira (company_id, nome) VALUES (%s, 'Material A')", (cid,)
        )
    app_user_conn.rollback()


def test_seed_de_categorias_idempotente_via_on_conflict(
    app_user_conn: psycopg.Connection, two_tenants: dict, despesas_por_tenant: dict
) -> None:
    """O índice `uq_categoria_company_nome` serve de alvo de ON CONFLICT: reaplicar o
    seed não duplica (nem com caixa diferente) e não levanta erro."""
    cid = two_tenants["A"]["company_id"]
    seed = (
        "INSERT INTO categoria_financeira (company_id, nome) "
        "SELECT %s, n FROM unnest(%s::text[]) AS n "
        "ON CONFLICT (company_id, lower(nome)) WHERE deleted_at IS NULL DO NOTHING"
    )
    nomes = ["Material", "Mão de obra", "MATERIAL A"]
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, cid)
        cur.execute(seed, (cid, nomes))
        cur.execute(seed, (cid, nomes))
        cur.execute("SELECT count(*) FROM categoria_financeira")
        # Material A (fixture) + Material + Mão de obra; 'MATERIAL A' não duplica a fixture
        assert cur.fetchone() == (3,)
    app_user_conn.rollback()


# ---- Policies e verificador ------------------------------------------------


@pytest.mark.parametrize("tabela", ["categoria_financeira", "despesa"])
def test_policy_das_tabelas_novas_usa_helper_e_rls_forcada(tabela: str) -> None:
    with SessionLocal() as s:
        rows = s.execute(
            text(
                "SELECT pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid) "
                "FROM pg_policy WHERE polrelid = CAST(:t AS regclass)"
            ),
            {"t": tabela},
        ).all()
        flags = s.execute(
            text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = CAST(:t AS regclass)"
            ),
            {"t": tabela},
        ).one()
    assert rows, f"{tabela} sem policy"
    assert flags == (True, True)
    for using, check in rows:
        assert using == check == "(company_id = app_current_company_id())"


def _erros_reais(*ddl: str) -> list[str]:
    """Muta o schema REAL numa transação, roda `verificar()` e reverte."""
    from scripts import check_schema_financeiro as chk

    from app.core.config import settings

    with psycopg.connect(settings.database_url_raw) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '5s'")
                for stmt in ddl:
                    cur.execute(stmt)
            return chk.verificar(conn)
        finally:
            conn.rollback()


def test_check_schema_cobre_tabelas_novas_e_passa_sem_mutacao() -> None:
    assert _erros_reais() == []


@pytest.mark.parametrize("tabela", ["categoria_financeira", "despesa"])
def test_check_schema_detecta_rls_nao_forcada_nas_tabelas_novas(tabela: str) -> None:
    erros = _erros_reais(f"ALTER TABLE {tabela} NO FORCE ROW LEVEL SECURITY")
    assert erros == [f"{tabela}: RLS não está habilitada E forçada (ENABLE + FORCE)"]


@pytest.mark.parametrize("tabela", ["categoria_financeira", "despesa"])
def test_check_schema_detecta_grant_ausente_nas_tabelas_novas(tabela: str) -> None:
    erros = _erros_reais(f"REVOKE DELETE ON {tabela} FROM app_user")
    assert erros == [f"{tabela}: falta GRANT DELETE para app_user"]


def test_check_schema_detecta_policy_sem_with_check_na_despesa() -> None:
    erros = _erros_reais(
        "DROP POLICY despesa_tenant_isolation ON despesa",
        "CREATE POLICY despesa_tenant_isolation ON despesa "
        "USING (company_id = app_current_company_id())",
    )
    assert any(
        e.startswith("despesa: policy despesa_tenant_isolation sem WITH CHECK") for e in erros
    )


@pytest.mark.parametrize(
    ("ddl", "tabela", "pai"),
    [
        (
            (
                "ALTER TABLE despesa DROP CONSTRAINT fk_despesa_obra",
                "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_obra FOREIGN KEY (obra_id) "
                "REFERENCES obras (id)",
            ),
            "despesa",
            "obras",
        ),
        (
            (
                "ALTER TABLE despesa DROP CONSTRAINT fk_despesa_obra_fase",
                "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_obra_fase FOREIGN KEY "
                "(obra_fase_id) REFERENCES obra_fase (id)",
            ),
            "despesa",
            "obra_fase",
        ),
        (
            (
                "ALTER TABLE obra_fase DROP CONSTRAINT fk_obra_fase_obra",
                "ALTER TABLE obra_fase ADD CONSTRAINT fk_obra_fase_obra FOREIGN KEY (obra_id) "
                "REFERENCES obras (id)",
            ),
            "obra_fase",
            "obras",
        ),
        (
            (
                "ALTER TABLE obra_fase DROP CONSTRAINT fk_obra_fase_orcamento_versao",
                "ALTER TABLE obra_fase ADD CONSTRAINT fk_obra_fase_orcamento_versao FOREIGN KEY "
                "(orcamento_versao_id) REFERENCES orcamento_versao (id)",
            ),
            "obra_fase",
            "orcamento_versao",
        ),
    ],
    ids=["despesa_obra", "despesa_fase", "obra_fase_obra", "obra_fase_versao"],
)
def test_check_schema_detecta_fk_simples_para_tabela_de_tenant(
    ddl: tuple[str, ...], tabela: str, pai: str
) -> None:
    """E-08: trocar uma FK composta por simples (para pai que tem company_id) é reprovado."""
    erros = _erros_reais(*ddl)
    assert len(erros) == 1, erros
    assert erros[0].startswith(f"{tabela}: FK ") and f"para {pai} (tabela de tenant)" in erros[0]


def test_check_schema_fk_para_users_e_excecao_explicita() -> None:
    """`created_by -> users(id)` é simples e NÃO falha (users não é tabela de tenant)."""
    assert _erros_reais() == []  # despesa_created_by_fkey existe e é simples
    with SessionLocal() as s:
        n = s.execute(
            text(
                "SELECT count(*) FROM pg_constraint WHERE conname = 'despesa_created_by_fkey' "
                "AND array_length(conkey, 1) = 1 AND confrelid = 'users'::regclass"
            )
        ).scalar_one()
    assert n == 1


def test_check_schema_sentinela_fk_composta_passa_e_simples_falha() -> None:
    erros = _erros_com_sentinela(
        "ALTER TABLE obra_fase_sentinela ADD COLUMN obra_id uuid",
        "ALTER TABLE obra_fase_sentinela ADD FOREIGN KEY (company_id, obra_id) "
        "REFERENCES obras (company_id, id)",
    )
    assert erros == ""
    erros = _erros_com_sentinela(
        "ALTER TABLE obra_fase_sentinela ADD COLUMN obra_id uuid",
        "ALTER TABLE obra_fase_sentinela ADD FOREIGN KEY (obra_id) REFERENCES obras (id)",
    )
    assert "FK obra_fase_sentinela_obra_id_fkey para obras (tabela de tenant)" in erros


# ---- E-08: FK composta de despesa.documento_id (faltava na parte de banco) ----


@pytest.fixture
def documentos_por_tenant(two_tenants: dict, fases_por_tenant: dict) -> dict[str, str]:
    """1 documento por tenant, na obra do tenant, via `obrax`. Cleanup: cascata."""
    out: dict[str, str] = {}
    with SessionLocal() as s:
        for label, tenant in two_tenants.items():
            out[label] = str(
                s.execute(
                    text(
                        "INSERT INTO documento (company_id, obra_id, nome, tipo) "
                        "VALUES (:c, :o, 'nf.pdf', 'nota_fiscal') RETURNING id"
                    ),
                    {"c": tenant["company_id"], "o": fases_por_tenant[label]["obra_id"]},
                ).scalar_one()
            )
        s.commit()
    return out


_INS_DESPESA_COM_DOC = (
    "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, fornecedor_nome, "
    "descricao, valor, data_competencia, vencimento, status, documento_id) "
    "VALUES (%s, %s, %s, %s, 'Forn', 'desc', 10.00, '2026-11-01', '2026-11-30', "
    "'prevista'::despesa_status, %s)"
)


def test_e08_despesa_de_a_apontando_para_documento_de_b_falha_por_fk(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    documentos_por_tenant: dict,
) -> None:
    """company_id = A, tudo de A, só o documento é de B: a policy aceita (company_id é
    A) e quem barra é a FK composta `(company_id, documento_id)`."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as exc:
        _exec_as(
            app_user_conn,
            two_tenants["A"]["company_id"],
            _INS_DESPESA_COM_DOC,
            (
                two_tenants["A"]["company_id"],
                fases_por_tenant["A"]["obra_id"],
                fases_por_tenant["A"]["fase_ids"][0],
                despesas_por_tenant["A"]["categoria_id"],
                documentos_por_tenant["B"],
            ),
        )
    assert exc.value.diag.constraint_name == "fk_despesa_documento"


def test_e08_despesa_de_a_apontando_para_documento_de_a_passa(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    documentos_por_tenant: dict,
) -> None:
    """Positivo: o mesmo INSERT com o documento de A passa e o vínculo fica gravado."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            _INS_DESPESA_COM_DOC + " RETURNING documento_id::text",
            (
                two_tenants["A"]["company_id"],
                fases_por_tenant["A"]["obra_id"],
                fases_por_tenant["A"]["fase_ids"][0],
                despesas_por_tenant["A"]["categoria_id"],
                documentos_por_tenant["A"],
            ),
        )
        assert cur.fetchone() == (documentos_por_tenant["A"],)
    app_user_conn.rollback()


# ---- E-11: despesa aponta para fase/documento da MESMA obra; texto não vazio ----


@pytest.fixture
def segunda_obra_de_a(two_tenants: dict, fases_por_tenant: dict) -> dict[str, str]:
    """Obra 2 do tenant A, com 1 fase e 1 documento, via `obrax`. Cleanup: cascata."""
    cid = two_tenants["A"]["company_id"]
    with SessionLocal() as s:
        cliente = s.execute(
            text("SELECT cliente_id FROM obras WHERE id = :o"),
            {"o": fases_por_tenant["A"]["obra_id"]},
        ).scalar_one()
        obra = s.execute(
            text(
                "INSERT INTO obras (company_id, cliente_id, codigo, nome) "
                "VALUES (:c, :cl, 'OB2-A', 'Obra 2 A') RETURNING id"
            ),
            {"c": cid, "cl": cliente},
        ).scalar_one()
        fase = s.execute(
            text(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, "
                "sort_order) VALUES (:c, :o, 'F001', 'Fase obra 2', 1, 0) RETURNING id"
            ),
            {"c": cid, "o": obra},
        ).scalar_one()
        doc = s.execute(
            text(
                "INSERT INTO documento (company_id, obra_id, nome, tipo) "
                "VALUES (:c, :o, 'nf.pdf', 'nota_fiscal') RETURNING id"
            ),
            {"c": cid, "o": obra},
        ).scalar_one()
        s.commit()
    return {"obra_id": str(obra), "fase_id": str(fase), "documento_id": str(doc)}


_INS_OBRA_FASE_DOC = (
    "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, fornecedor_nome, "
    "descricao, valor, data_competencia, vencimento, status, documento_id) "
    "VALUES (%s, %s, %s, %s, 'Forn', 'desc', 10.00, '2026-11-01', '2026-11-30', "
    "'prevista'::despesa_status, %s)"
)


def _params_obra_fase_doc(
    two_tenants: dict,
    fases: dict,
    desp: dict,
    obra: str,
    fase: str,
    documento: str | None,
) -> tuple:
    return (
        two_tenants["A"]["company_id"],
        obra,
        fase,
        desp["A"]["categoria_id"],
        documento,
    )


def test_despesa_com_fase_de_outra_obra_da_mesma_empresa_falha_por_fk(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    segunda_obra_de_a: dict,
) -> None:
    a = fases_por_tenant["A"]
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as exc:
        _exec_as(
            app_user_conn,
            two_tenants["A"]["company_id"],
            _INS_OBRA_FASE_DOC,
            _params_obra_fase_doc(
                two_tenants,
                fases_por_tenant,
                despesas_por_tenant,
                a["obra_id"],
                segunda_obra_de_a["fase_id"],
                None,
            ),
        )
    assert exc.value.diag.constraint_name == "fk_despesa_obra_fase"


def test_despesa_com_documento_de_outra_obra_da_mesma_empresa_falha_por_fk(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    segunda_obra_de_a: dict,
) -> None:
    a = fases_por_tenant["A"]
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as exc:
        _exec_as(
            app_user_conn,
            two_tenants["A"]["company_id"],
            _INS_OBRA_FASE_DOC,
            _params_obra_fase_doc(
                two_tenants,
                fases_por_tenant,
                despesas_por_tenant,
                a["obra_id"],
                a["fase_ids"][0],
                segunda_obra_de_a["documento_id"],
            ),
        )
    assert exc.value.diag.constraint_name == "fk_despesa_documento"


def test_despesa_com_fase_e_documento_da_mesma_obra_passa_na_obra_2(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    segunda_obra_de_a: dict,
) -> None:
    """Positivo: obra 2 com a fase e o documento da obra 2 passa."""
    with app_user_conn.transaction(), app_user_conn.cursor() as cur:
        _ctx(cur, two_tenants["A"]["company_id"])
        cur.execute(
            _INS_OBRA_FASE_DOC + " RETURNING obra_id::text",
            _params_obra_fase_doc(
                two_tenants,
                fases_por_tenant,
                despesas_por_tenant,
                segunda_obra_de_a["obra_id"],
                segunda_obra_de_a["fase_id"],
                segunda_obra_de_a["documento_id"],
            ),
        )
        assert cur.fetchone() == (segunda_obra_de_a["obra_id"],)
    app_user_conn.rollback()


@pytest.mark.parametrize(
    ("sql", "constraint"),
    [
        (
            "INSERT INTO categoria_financeira (company_id, nome) VALUES (%s, '   ')",
            "ck_categoria_nome_nao_vazio",
        ),
        (
            "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, "
            "fornecedor_nome, descricao, valor, data_competencia, vencimento, status) "
            "VALUES (%s, %s, %s, %s, '   ', 'd', 1, '2026-11-01', '2026-11-30', 'prevista')",
            "ck_despesa_fornecedor_nao_vazio",
        ),
        (
            "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, "
            "fornecedor_nome, descricao, valor, data_competencia, vencimento, status) "
            "VALUES (%s, %s, %s, %s, 'F', '  ', 1, '2026-11-01', '2026-11-30', 'prevista')",
            "ck_despesa_descricao_nao_vazia",
        ),
    ],
    ids=["categoria_nome", "despesa_fornecedor", "despesa_descricao"],
)
def test_check_texto_obrigatorio_nao_pode_ser_so_espaco(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    fases_por_tenant: dict,
    despesas_por_tenant: dict,
    sql: str,
    constraint: str,
) -> None:
    a = two_tenants["A"]["company_id"]
    params: tuple = (a,)
    if "INTO despesa" in sql:
        params = (
            a,
            fases_por_tenant["A"]["obra_id"],
            fases_por_tenant["A"]["fase_ids"][0],
            despesas_por_tenant["A"]["categoria_id"],
        )
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        _exec_as(app_user_conn, a, sql, params)
    assert exc.value.diag.constraint_name == constraint
