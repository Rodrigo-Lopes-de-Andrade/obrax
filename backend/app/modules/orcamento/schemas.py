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


# --------------------------------------------------------------------------- #
# Itens EAP (B5.4, US-12)
# --------------------------------------------------------------------------- #
ItemTipo = Literal["F", "S", "I"]  # Fase, Serviço, Insumo/MO


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: ItemTipo
    # parent_id deve referenciar um item existente da mesma versão (F→S→I).
    parent_id: UUID | None = None
    codigo: str | None = Field(default=None, max_length=60)
    descricao: str = Field(min_length=1, max_length=300)
    unidade: str | None = Field(default=None, max_length=20)
    quantidade: Decimal = Field(default=Decimal(0), ge=0, max_digits=10, decimal_places=4)
    preco_unitario: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=6)
    markup_override: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=4)


class ItensBulkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[ItemCreate] = Field(min_length=1, max_length=1000)


class ItemUpdate(BaseModel):
    """PATCH parcial — só os campos enviados são alterados (`exclude_unset`)."""

    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, max_length=60)
    descricao: str | None = Field(default=None, min_length=1, max_length=300)
    unidade: str | None = Field(default=None, max_length=20)
    quantidade: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=4)
    preco_unitario: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    markup_override: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=4)


class ReorderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_id: UUID | None = None
    sort_order: int = Field(ge=0)


class ReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[ReorderItem] = Field(min_length=1, max_length=2000)


class PrecificacaoUpdate(BaseModel):
    """Markup global + taxa administrativa da versão (aba Precificação, F5.3)."""

    model_config = ConfigDict(extra="forbid")

    markup_global: Decimal = Field(ge=0, max_digits=5, decimal_places=4)
    taxa_adm: Decimal = Field(ge=0, max_digits=5, decimal_places=4)


class ItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    versao_id: UUID
    parent_id: UUID | None
    tipo: ItemTipo
    depth: int
    path: str
    sort_order: int
    codigo: str | None
    descricao: str
    unidade: str | None
    quantidade: Decimal
    preco_unitario: Decimal
    markup_override: Decimal | None
    custo_total: Decimal
    subtotal: Decimal


class VersaoResumo(BaseModel):
    """Agregados da versão para o builder (sem numero/created_at)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    is_locked: bool
    custo_direto: Decimal
    markup_global: Decimal
    taxa_adm: Decimal
    preco_venda: Decimal
    margem: Decimal


class EapTree(BaseModel):
    """Árvore EAP recalculada — corpo devolvido pelo GET e por toda mutação de
    itens (a UI re-renderiza a partir da verdade do servidor). Itens em ordem de
    árvore (path)."""

    model_config = ConfigDict(extra="forbid")

    versao: VersaoResumo
    itens: list[ItemOut]
