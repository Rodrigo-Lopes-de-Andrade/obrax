"""Schemas Pydantic do Módulo 2 (Orçamentos).

Valores financeiros são `Decimal` (Pydantic v2 serializa em JSON como string —
mantém o contrato do frontend, que usa Decimal.js). **Float é proibido** em
qualquer cálculo/serialização de dinheiro (docs/CLAUDE.md).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OrcamentoStatus = Literal["rascunho", "em_revisao", "aguardando_aprovacao", "aprovado", "rejeitado"]


# --------------------------------------------------------------------------- #
# Motor de cálculo (B5.2)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# CRUD de orçamento (B5.3, US-11)
# --------------------------------------------------------------------------- #
class OrcamentoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)


class OrcamentoStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrcamentoStatus


class VersaoOut(BaseModel):
    """Agregados de uma versão do orçamento (recalculados pelo BudgetCalculator)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    numero: int
    is_locked: bool
    custo_direto: Decimal
    markup_global: Decimal
    taxa_adm: Decimal
    preco_venda: Decimal
    margem: Decimal
    created_at: datetime


class OrcamentoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    titulo: str
    status: OrcamentoStatus
    versao_atual: int
    created_at: datetime


class OrcamentoDetail(OrcamentoOut):
    """Orçamento + a versão atual (agregados) — corpo do GET /{id}."""

    versao: VersaoOut


class OrcamentoPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OrcamentoOut]
    next_cursor: str | None
