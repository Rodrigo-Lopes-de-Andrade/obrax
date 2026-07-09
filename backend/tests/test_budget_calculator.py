"""B5.2 — BudgetCalculator: recálculo em cascata, precedência de markup,
precisão Decimal e alvo de performance (1000 itens < 300ms).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.modules.orcamento.services import budget_calculator

_INSERT_ITEM = text(
    "INSERT INTO orcamento_item "
    "(id, company_id, versao_id, parent_id, tipo, descricao, "
    " quantidade, preco_unitario, markup_override, path, depth) "
    "VALUES (:id, :cid, :vid, :parent, :tipo, :descricao, "
    " :qtd, :preco, :markup, '', 0)"
)


@pytest.fixture
def versao_factory(seed_tenant: Callable[..., Any]) -> Iterator[Callable[..., dict[str, Any]]]:
    """Cria company+obra+orcamento+versão (via `obrax`, bypassa RLS). Cleanup
    dos itens/versões cascateia pelo teardown de `seed_tenant` (delete company)."""

    def _make(*, markup_global: str = "0", taxa_adm: str = "0") -> dict[str, Any]:
        tenant = seed_tenant()
        cid = tenant.company_id
        with SessionLocal() as session:
            cliente_id = session.execute(
                text(
                    "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
                    "VALUES (:cid, 'PF', '52998224725', 'C') RETURNING id"
                ),
                {"cid": cid},
            ).scalar_one()
            obra_id = session.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, codigo, nome) "
                    "VALUES (:cid, :cl, 'OB-1', 'Obra') RETURNING id"
                ),
                {"cid": cid, "cl": cliente_id},
            ).scalar_one()
            orc_id = session.execute(
                text(
                    "INSERT INTO orcamento (company_id, obra_id, titulo) "
                    "VALUES (:cid, :ob, 'Orç') RETURNING id"
                ),
                {"cid": cid, "ob": obra_id},
            ).scalar_one()
            vid = session.execute(
                text(
                    "INSERT INTO orcamento_versao "
                    "(company_id, orcamento_id, numero, markup_global, taxa_adm) "
                    "VALUES (:cid, :orc, 1, :mg, :ta) RETURNING id"
                ),
                {"cid": cid, "orc": orc_id, "mg": markup_global, "ta": taxa_adm},
            ).scalar_one()
            session.commit()
        return {"company_id": cid, "versao_id": vid}

    yield _make


def _add(
    company_id: str,
    versao_id: uuid.UUID,
    tipo: str,
    *,
    parent: uuid.UUID | None = None,
    qtd: str = "0",
    preco: str = "0",
    markup: str | None = None,
) -> uuid.UUID:
    with SessionLocal() as session:
        new_id = uuid.uuid4()
        session.execute(
            _INSERT_ITEM,
            {
                "id": new_id,
                "cid": company_id,
                "vid": versao_id,
                "parent": parent,
                "tipo": tipo,
                "descricao": f"{tipo}-item",
                "qtd": qtd,
                "preco": preco,
                "markup": markup,
            },
        )
        session.commit()
    return new_id


def test_recalc_cascata_com_precedencia_de_markup(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    ctx = versao_factory(markup_global="0.20", taxa_adm="0.05")
    cid, vid = ctx["company_id"], ctx["versao_id"]

    f1 = _add(cid, vid, "F")
    s1 = _add(cid, vid, "S", parent=f1)
    i1 = _add(cid, vid, "I", parent=s1, qtd="10", preco="100.00")  # markup global 0.20
    i2 = _add(cid, vid, "I", parent=s1, qtd="5", preco="50.00", markup="0.50")  # override item
    f2 = _add(cid, vid, "F", markup="0.10")  # override na fase
    s2 = _add(cid, vid, "S", parent=f2)
    i3 = _add(cid, vid, "I", parent=s2, qtd="2", preco="200.00")  # herda fase 0.10

    with SessionLocal() as session:
        snap = budget_calculator.recalcular(session, vid)
        session.commit()

    by_id = {it.id: it.subtotal for it in snap.itens}
    assert by_id[i1] == Decimal("1200.00")  # 1000 × 1.20
    assert by_id[i2] == Decimal("375.00")  # 250 × 1.50 (override do item)
    assert by_id[s1] == Decimal("1575.00")
    assert by_id[f1] == Decimal("1575.00")
    assert by_id[i3] == Decimal("440.00")  # 400 × 1.10 (herda markup da fase)
    assert by_id[s2] == Decimal("440.00")
    assert by_id[f2] == Decimal("440.00")

    assert snap.custo_direto == Decimal("1650.00")  # 1000 + 250 + 400
    assert snap.preco_venda == Decimal("2115.75")  # 2015 × 1.05 (taxa adm)
    assert snap.margem == Decimal("0.2201")  # 465.75 / 2115.75

    # Persistiu no banco (subtotal do item e agregados da versão).
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT preco_venda, custo_direto FROM orcamento_versao WHERE id = :v"),
            {"v": vid},
        ).one()
        assert row.preco_venda == Decimal("2115.75")
        item_sub = session.execute(
            text("SELECT subtotal FROM orcamento_item WHERE id = :i"), {"i": i1}
        ).scalar_one()
        assert item_sub == Decimal("1200.00")


def test_markup_por_fase_denormalizado(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    """B6.2 — markup por fase (override fase ?? global) + custo/subtotal agregados
    persistidos em markup_por_fase_json, na mesma transação do recálculo."""
    ctx = versao_factory(markup_global="0.20")
    cid, vid = ctx["company_id"], ctx["versao_id"]

    f1 = _add(cid, vid, "F")  # sem override → herda global 0.20
    s1 = _add(cid, vid, "S", parent=f1)
    _add(cid, vid, "I", parent=s1, qtd="10", preco="100.00")  # 1000
    _add(cid, vid, "I", parent=s1, qtd="5", preco="50.00", markup="0.50")  # override item
    f2 = _add(cid, vid, "F", markup="0.10")  # override na fase
    s2 = _add(cid, vid, "S", parent=f2)
    _add(cid, vid, "I", parent=s2, qtd="2", preco="200.00")  # 400

    with SessionLocal() as session:
        budget_calculator.recalcular(session, vid)
        session.commit()

    with SessionLocal() as session:
        fases = session.execute(
            text("SELECT markup_por_fase_json FROM orcamento_versao WHERE id = :v"),
            {"v": vid},
        ).scalar_one()

    por_id = {f["id"]: f for f in fases}
    # Fase 1: markup do nível da fase é o global (0.20); item override não muda
    # o markup da FASE, mas o subtotal reflete a cascata (1200 + 375 = 1575).
    assert por_id[str(f1)]["markup"] == "0.2000"
    assert por_id[str(f1)]["custo"] == "1250.00"
    assert por_id[str(f1)]["subtotal"] == "1575.00"
    # Fase 2: override da própria fase (0.10) prevalece sobre o global.
    assert por_id[str(f2)]["markup"] == "0.1000"
    assert por_id[str(f2)]["custo"] == "400.00"
    assert por_id[str(f2)]["subtotal"] == "440.00"


def test_recalc_versao_vazia_zera_agregados(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    ctx = versao_factory(markup_global="0.30")
    with SessionLocal() as session:
        snap = budget_calculator.recalcular(session, ctx["versao_id"])
        session.commit()
    assert snap.custo_direto == Decimal("0")
    assert snap.preco_venda == Decimal("0.00")
    assert snap.margem == Decimal("0.0000")
    assert snap.itens == []


def test_recalc_versao_travada_bloqueia(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    ctx = versao_factory()
    with SessionLocal() as session:
        session.execute(
            text("UPDATE orcamento_versao SET is_locked = true WHERE id = :v"),
            {"v": ctx["versao_id"]},
        )
        session.commit()
    with pytest.raises(Exception, match="imutável"):
        with SessionLocal() as session:
            budget_calculator.recalcular(session, ctx["versao_id"])


def test_recalc_versao_inexistente_404(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    versao_factory()  # garante contexto de tenant válido na sessão
    with pytest.raises(Exception, match="não encontrada"):
        with SessionLocal() as session:
            budget_calculator.recalcular(session, uuid.uuid4())


def test_recalc_1000_itens_sub_300ms(
    versao_factory: Callable[..., dict[str, Any]],
) -> None:
    """Alvo do critério de aceite B5.2: 1000 itens recalculados < 300ms."""
    ctx = versao_factory(markup_global="0.25", taxa_adm="0.08")
    cid, vid = ctx["company_id"], ctx["versao_id"]

    # 10 fases × 10 serviços × 10 insumos = 1000 folhas (1110 nós no total).
    bulk: list[dict[str, Any]] = []
    for _ in range(10):
        fid = uuid.uuid4()
        bulk.append({"id": fid, "parent": None, "tipo": "F", "qtd": "0", "preco": "0"})
        for _ in range(10):
            sid = uuid.uuid4()
            bulk.append({"id": sid, "parent": fid, "tipo": "S", "qtd": "0", "preco": "0"})
            for _ in range(10):
                bulk.append(
                    {
                        "id": uuid.uuid4(),
                        "parent": sid,
                        "tipo": "I",
                        "qtd": "3.5",
                        "preco": "12.750000",
                    }
                )
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO orcamento_item "
                "(id, company_id, versao_id, parent_id, tipo, descricao, "
                " quantidade, preco_unitario, path, depth) "
                "VALUES (:id, :cid, :vid, :parent, :tipo, 'x', :qtd, :preco, '', 0)"
            ),
            [{**b, "cid": cid, "vid": vid} for b in bulk],
        )
        session.commit()

    with SessionLocal() as session:
        start = time.perf_counter()
        snap = budget_calculator.recalcular(session, vid)
        session.commit()
        elapsed = time.perf_counter() - start

    # 1000 folhas × (3.5 × 12.75 = 44.625 → custo 44.62/44.63) — só checa ordem
    # de grandeza e o alvo de tempo; a exatidão está no teste determinístico.
    assert len(snap.itens) == 1110
    assert snap.preco_venda > Decimal("0")
    assert elapsed < 0.3, f"recalc de 1000 itens levou {elapsed * 1000:.0f}ms (alvo <300ms)"
