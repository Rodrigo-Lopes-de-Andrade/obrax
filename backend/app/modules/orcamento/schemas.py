"""Schemas Pydantic do Módulo 2 (Orçamentos).

Valores financeiros são `Decimal` (Pydantic v2 serializa em JSON como string —
mantém o contrato do frontend, que usa Decimal.js). **Float é proibido** em
qualquer cálculo/serialização de dinheiro (docs/CLAUDE.md).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ItemSubtotal(BaseModel):
    """Subtotal (com markup) recalculado de um item, por id."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    subtotal: Decimal


class BudgetSnapshot(BaseModel):
    """Retorno do BudgetCalculator (B5.2): agregados da versão + subtotais por
    item. É o corpo devolvido pelos endpoints que disparam recálculo (bulk de
    itens, precificação — B5.4)."""

    model_config = ConfigDict(extra="forbid")

    versao_id: UUID
    custo_direto: Decimal
    markup_global: Decimal
    taxa_adm: Decimal
    preco_venda: Decimal
    margem: Decimal
    itens: list[ItemSubtotal]
