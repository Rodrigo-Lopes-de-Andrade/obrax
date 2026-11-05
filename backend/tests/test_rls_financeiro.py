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
