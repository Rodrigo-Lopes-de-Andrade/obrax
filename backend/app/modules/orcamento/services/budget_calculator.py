"""B5.2 — BudgetCalculator: recálculo em cascata dos subtotais de uma versão.

Fluxo (docs/ESPEC.md § 7 › Motor de cálculo):
    1. custo_total = quantidade × preco_unitario          [Decimal, precisão plena]
    2. effective_markup = item.override ?? ancestral.override ?? markup_global
       subtotal_folha = custo_total × (1 + effective_markup)
    3. taxa_adm aplicada sobre o total (soma das fases)
    4. agrega bottom-up: insumo → serviço → fase → total
    Transação: SELECT ... FOR UPDATE na versão → persiste subtotais → snapshot

Regras:
- **Proibido float.** Tudo em `Decimal`; arredonda para (18,2) só ao gravar cada
  linha (uma vez), evitando drift de centavos acumulado.
- Versão aprovada (`is_locked`) é imutável: o recálculo grava subtotais, logo é
  barrado (409) antes de qualquer escrita — o trigger do banco é o backstop.
- `effective_markup` usa o override do ancestral mais próximo (item → serviço →
  fase), caindo no `markup_global` da versão.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Numeric, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Session

from app.modules.orcamento.schemas import BudgetSnapshot, ItemSubtotal

_CENT = Decimal("0.01")
_RATE = Decimal("0.0001")
_ONE = Decimal(1)

VERSAO_TRAVADA = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="versão aprovada é imutável"
)
VERSAO_NAO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="versão não encontrada"
)

# Trava a linha da versão até o commit (serializa recálculos concorrentes).
_LOCK_VERSAO = text(
    "SELECT markup_global, taxa_adm, is_locked FROM orcamento_versao WHERE id = :vid FOR UPDATE"
)
_LOAD_ITENS = text(
    "SELECT id, parent_id, quantidade, preco_unitario, markup_override "
    "FROM orcamento_item WHERE versao_id = :vid"
)
# Um único UPDATE p/ N linhas via unnest de arrays paralelos (id, subtotal).
_BULK_UPDATE_SUBTOTAL = text(
    "UPDATE orcamento_item AS oi SET subtotal = data.subtotal "
    "FROM unnest(:ids, :subs) AS data(id, subtotal) WHERE oi.id = data.id"
).bindparams(
    bindparam("ids", type_=ARRAY(PgUUID(as_uuid=True))),
    bindparam("subs", type_=ARRAY(Numeric(18, 2))),
)
_UPDATE_VERSAO = text(
    "UPDATE orcamento_versao "
    "SET custo_direto = :cd, preco_venda = :pv, margem = :mg WHERE id = :vid"
)


def recalcular(session: Session, versao_id: uuid.UUID) -> BudgetSnapshot:
    """Recalcula subtotais (com markup) da versão e seus agregados, persiste e
    devolve o snapshot. Não faz commit — o chamador controla a transação."""
    versao = session.execute(_LOCK_VERSAO, {"vid": versao_id}).mappings().first()
    if versao is None:
        raise VERSAO_NAO_ENCONTRADA
    if versao["is_locked"]:
        raise VERSAO_TRAVADA

    global_markup: Decimal = versao["markup_global"]
    taxa_adm: Decimal = versao["taxa_adm"]

    rows = session.execute(_LOAD_ITENS, {"vid": versao_id}).mappings().all()
    by_id: dict[uuid.UUID, Any] = {r["id"]: r for r in rows}
    children: dict[uuid.UUID | None, list[Any]] = defaultdict(list)
    for r in rows:
        children[r["parent_id"]].append(r)

    subtotal: dict[uuid.UUID, Decimal] = {}
    custo_direto = Decimal(0)

    def effective_markup(node: Any) -> Decimal:
        cur: Any | None = node
        while cur is not None:
            override = cur["markup_override"]
            if override is not None:
                return override  # type: ignore[no-any-return]
            cur = by_id.get(cur["parent_id"])
        return global_markup

    def walk(node: Any) -> Decimal:
        nonlocal custo_direto
        kids = children.get(node["id"])
        if kids:
            total = sum((walk(k) for k in kids), Decimal(0))
        else:
            # Folha (insumo/MO): custo direto em precisão plena; arredonda 1× ao
            # aplicar markup. custo_direto acumula o custo já em centavos (casa
            # com a coluna GENERATED custo_total NUMERIC(18,2)).
            custo = node["quantidade"] * node["preco_unitario"]
            custo_direto += custo.quantize(_CENT, ROUND_HALF_UP)
            markup = effective_markup(node)
            total = (custo * (_ONE + markup)).quantize(_CENT, ROUND_HALF_UP)
        subtotal[node["id"]] = total
        return total

    total_com_markup = sum((walk(r) for r in children.get(None, [])), Decimal(0))
    preco_venda = (total_com_markup * (_ONE + taxa_adm)).quantize(_CENT, ROUND_HALF_UP)
    margem = (
        ((preco_venda - custo_direto) / preco_venda).quantize(_RATE, ROUND_HALF_UP)
        if preco_venda > 0
        else Decimal("0.0000")
    )

    if subtotal:
        session.execute(
            _BULK_UPDATE_SUBTOTAL,
            {"ids": list(subtotal.keys()), "subs": list(subtotal.values())},
        )
    session.execute(
        _UPDATE_VERSAO,
        {"cd": custo_direto, "pv": preco_venda, "mg": margem, "vid": versao_id},
    )

    return BudgetSnapshot(
        versao_id=versao_id,
        custo_direto=custo_direto,
        markup_global=global_markup,
        taxa_adm=taxa_adm,
        preco_venda=preco_venda,
        margem=margem,
        itens=[ItemSubtotal(id=i, subtotal=s) for i, s in subtotal.items()],
    )
