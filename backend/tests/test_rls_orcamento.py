"""B5.1 — schema e isolamento (RLS) de orcamento / orcamento_versao /
orcamento_item, mais as invariantes de DDL: `custo_total` GENERATED e o trigger
de bloqueio de versão aprovada (`is_locked`).

Mesma abordagem de test_rls_tickets: semeia via role `obrax` (bypassa RLS) e
valida a leitura/escrita sob `app_user` (sujeito a RLS).
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import psycopg
import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture
def orcamentos_por_tenant(two_tenants: dict) -> Iterator[dict[str, dict[str, str]]]:
    """cliente + obra + orcamento + versão 1 + 1 item (fase) por tenant."""
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
            orc_id = session.execute(
                text(
                    "INSERT INTO orcamento (company_id, obra_id, titulo) "
                    "VALUES (:cid, :obra_id, :titulo) RETURNING id"
                ),
                {"cid": cid, "obra_id": obra_id, "titulo": f"Orçamento {label}"},
            ).scalar_one()
            versao_id = session.execute(
                text(
                    "INSERT INTO orcamento_versao (company_id, orcamento_id, numero) "
                    "VALUES (:cid, :orc_id, 1) RETURNING id"
                ),
                {"cid": cid, "orc_id": orc_id},
            ).scalar_one()
            item_id = session.execute(
                text(
                    "INSERT INTO orcamento_item "
                    "(company_id, versao_id, tipo, descricao, path, depth) "
                    "VALUES (:cid, :vid, 'F', :d, '', 0) RETURNING id"
                ),
                {"cid": cid, "vid": versao_id, "d": f"Fase {label}"},
            ).scalar_one()
            seeded[label] = {
                "obra_id": str(obra_id),
                "orcamento_id": str(orc_id),
                "versao_id": str(versao_id),
                "item_id": str(item_id),
            }
        session.commit()
    yield seeded


def _ids_as_tenant(conn: psycopg.Connection, company_id: str, sql: str) -> set[str]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
            cur.execute(sql)
            return {str(r[0]) for r in cur.fetchall()}


@pytest.mark.parametrize(
    "table, key",
    [
        ("orcamento", "orcamento_id"),
        ("orcamento_versao", "versao_id"),
        ("orcamento_item", "item_id"),
    ],
)
def test_isolation(
    app_user_conn: psycopg.Connection,
    two_tenants: dict,
    orcamentos_por_tenant: dict,
    table: str,
    key: str,
) -> None:
    ids_a = _ids_as_tenant(app_user_conn, two_tenants["A"]["company_id"], f"SELECT id FROM {table}")
    assert ids_a == {orcamentos_por_tenant["A"][key]}
    assert orcamentos_por_tenant["B"][key] not in ids_a


def test_fail_closed_sem_tenant(
    app_user_conn: psycopg.Connection, orcamentos_por_tenant: dict
) -> None:
    with app_user_conn.transaction():
        with app_user_conn.cursor() as cur:
            for table in ("orcamento", "orcamento_versao", "orcamento_item"):
                cur.execute(f"SELECT id FROM {table}")
                assert cur.fetchall() == []


def test_insert_cross_tenant_bloqueado(
    app_user_conn: psycopg.Connection, two_tenants: dict, orcamentos_por_tenant: dict
) -> None:
    with pytest.raises(psycopg.errors.Error):
        with app_user_conn.transaction():
            with app_user_conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.company_id', %s, true)",
                    (two_tenants["A"]["company_id"],),
                )
                cur.execute(
                    "INSERT INTO orcamento (company_id, obra_id, titulo) VALUES (%s, %s, 'intruso')",
                    (two_tenants["B"]["company_id"], orcamentos_por_tenant["B"]["obra_id"]),
                )


def test_custo_total_generated(orcamentos_por_tenant: dict) -> None:
    """custo_total = quantidade × preco_unitario (coluna GENERATED, sem Python)."""
    vid = orcamentos_por_tenant["A"]["versao_id"]
    cid = None
    with SessionLocal() as session:
        cid = session.execute(
            text("SELECT company_id FROM orcamento_versao WHERE id = :v"), {"v": vid}
        ).scalar_one()
        custo = session.execute(
            text(
                "INSERT INTO orcamento_item "
                "(company_id, versao_id, tipo, descricao, quantidade, preco_unitario, path, depth) "
                "VALUES (:cid, :vid, 'I', 'Cimento', 12.5, 33.750000, '', 2) "
                "RETURNING custo_total"
            ),
            {"cid": cid, "vid": vid},
        ).scalar_one()
        session.commit()
    assert custo == Decimal("421.88")  # 12.5 × 33.75 = 421.875 → arredonda p/ (18,2)


def test_trigger_bloqueia_edicao_de_versao_travada(orcamentos_por_tenant: dict) -> None:
    """Versão aprovada (is_locked) é imutável: UPDATE/DELETE em item falha."""
    vid = orcamentos_por_tenant["A"]["versao_id"]
    item_id = orcamentos_por_tenant["A"]["item_id"]
    with SessionLocal() as session:
        session.execute(
            text("UPDATE orcamento_versao SET is_locked = true WHERE id = :v"), {"v": vid}
        )
        session.commit()
    with pytest.raises(Exception, match="versao_travada"):
        with SessionLocal() as session:
            session.execute(
                text("UPDATE orcamento_item SET descricao = 'x' WHERE id = :i"), {"i": item_id}
            )
            session.commit()
