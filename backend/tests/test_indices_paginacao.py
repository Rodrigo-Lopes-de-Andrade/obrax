"""D2.2 — validação dos índices de paginação por cursor (migration 0013).

Semeia um tenant-alvo pequeno (A) e um tenant grande (B, inserido depois → ids
UUIDv7 maiores), de modo que a listagem de A por `ORDER BY id DESC` precise
"passar por cima" das linhas de B se varrer a PK. Com o índice parcial
`(company_id, id DESC) WHERE deleted_at IS NULL` de 0013, o planner escolhe um
Index Scan escopado por `company_id`, com a ordem satisfeita pelo índice — sem
Seq Scan e sem Sort. Esse é o critério de aceite do D2.2 ("index scan, não seq
scan") no shape real da query (obras/service.py e clientes/service.py).
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal

# Colunas reais das listagens (obras/service.py, clientes/service.py) — mantê-las
# garante que o EXPLAIN reflita o mesmo shape de SELECT em produção.
OBRAS_COLS = (
    "id, cliente_id, status, codigo, nome, data_inicio, data_prevista_fim, "
    "data_real_fim, valor_contrato, created_at"
)
CLIENTES_COLS = "id, tipo_pessoa, documento, nome, telefone, email, created_at"

OBRAS_LIST_SQL = (
    f"SELECT {OBRAS_COLS} FROM obras WHERE deleted_at IS NULL "
    "  AND (CAST(NULL AS uuid) IS NULL OR id < CAST(NULL AS uuid)) "
    "  AND (CAST(NULL AS obra_status) IS NULL OR status = CAST(NULL AS obra_status)) "
    "  AND (CAST(NULL AS uuid) IS NULL OR cliente_id = CAST(NULL AS uuid)) "
    "ORDER BY id DESC LIMIT 51"
)
CLIENTES_LIST_SQL = (
    f"SELECT {CLIENTES_COLS} FROM clientes WHERE deleted_at IS NULL "
    "  AND (CAST(NULL AS uuid) IS NULL OR id < CAST(NULL AS uuid)) "
    "  AND (CAST(NULL AS text) IS NULL OR tipo_pessoa = CAST(NULL AS text)) "
    "  AND (CAST(NULL AS text) IS NULL OR nome ILIKE CAST(NULL AS text) "
    "       OR documento ILIKE CAST(NULL AS text)) "
    "ORDER BY id DESC LIMIT 51"
)


def _cpf(base9: str) -> str:
    d = base9
    for length in (9, 10):
        total = sum(int(d[i]) * (length + 1 - i) for i in range(length))
        d += str((total * 10) % 11 % 10)
    return d


@pytest.fixture
def dataset_paginacao(two_tenants: dict) -> Iterator[dict[str, str]]:
    """A pequeno (8), B grande (150) em clientes e obras. Ordem de inserção
    A→B garante que os ids de B sejam maiores (mais novos). ANALYZE para o
    planner ter estatísticas. Cleanup pelo cascade de `two_tenants`."""
    a_cid = two_tenants["A"]["company_id"]
    b_cid = two_tenants["B"]["company_id"]
    seq = iter(range(1, 10_000))
    with SessionLocal() as s:

        def seed_clientes(company_id: str, n: int) -> str:
            first: str | None = None
            for _ in range(n):
                doc = _cpf(f"{next(seq):09d}")
                cid = s.execute(
                    text(
                        "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                        "VALUES (:co, 'PF', :d, 'C') RETURNING id"
                    ),
                    {"co": company_id, "d": doc},
                ).scalar_one()
                first = first or str(cid)
            assert first is not None
            return first

        def seed_obras(company_id: str, cliente_id: str, n: int) -> None:
            s.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, status, codigo, nome) "
                    "SELECT :co, :cl, "
                    "  (ARRAY['planejamento','execucao','pausada','concluida','cancelada']"
                    "   )[1 + (g % 5)]::obra_status, "
                    "  'OB-' || g, 'O' "
                    "FROM generate_series(1, :n) g"
                ),
                {"co": company_id, "cl": cliente_id, "n": n},
            )

        a_cliente = seed_clientes(a_cid, 8)
        b_cliente = seed_clientes(b_cid, 150)
        seed_obras(a_cid, a_cliente, 8)
        seed_obras(b_cid, b_cliente, 150)
        s.execute(text("ANALYZE clientes"))
        s.execute(text("ANALYZE obras"))
        s.commit()

    yield {"a_company_id": a_cid}


def _plan(conn: psycopg.Connection, company_id: str, sql: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
        # Em escala de teste (dezenas de linhas) seq scan e bitmap scan são
        # legitimamente mais baratos que um Index Scan ordenado (o custo por
        # linha de acesso random ao heap só compensa em escala, via early-stop do
        # LIMIT). Desligá-los (SET LOCAL, escopo da transação) força a escolha
        # entre Index Scans puros, revelando qual índice serve a query: com o
        # tenant-alvo pequeno e o outro maior/mais novo, o índice de 0013
        # (company_id, id DESC) vence a PK (não precisa pular as linhas do outro
        # tenant) e o índice (company_id, created_at DESC) (dispensa o Sort).
        cur.execute("SET LOCAL enable_seqscan = off")
        cur.execute("SET LOCAL enable_bitmapscan = off")
        cur.execute("EXPLAIN " + sql)
        return "\n".join(r[0] for r in cur.fetchall())


def test_obras_lista_usa_indice_sem_sort(
    app_user_conn: psycopg.Connection, dataset_paginacao: dict
) -> None:
    plan = _plan(app_user_conn, dataset_paginacao["a_company_id"], OBRAS_LIST_SQL)
    assert "ix_obras_company_id_desc" in plan, plan
    assert "Seq Scan" not in plan, plan
    assert "Sort" not in plan, plan  # ordem satisfeita pelo índice


def test_clientes_lista_usa_indice_sem_sort(
    app_user_conn: psycopg.Connection, dataset_paginacao: dict
) -> None:
    plan = _plan(app_user_conn, dataset_paginacao["a_company_id"], CLIENTES_LIST_SQL)
    assert "ix_clientes_company_id_desc" in plan, plan
    assert "Seq Scan" not in plan, plan
    assert "Sort" not in plan, plan
