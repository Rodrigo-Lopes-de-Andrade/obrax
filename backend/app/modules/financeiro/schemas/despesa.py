"""Schemas de categoria e despesa (ESPEC §6.2, Dicionário §4.2-4.3).

Dinheiro é `Decimal` (NUMERIC(18,2)). Fornecedor é texto livre (ESPEC §8);
`fornecedor_id` só é devolvido, não aceito na entrada, até a US-03 existir.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.financeiro.schemas._types import (
    DespesaStatus,
    DinheiroOut,
    DinheiroPositivo,
    omitido,
)


class CategoriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=120)


class CategoriaUpdate(BaseModel):
    """Renomear, ativar ou desativar. Campo omitido não muda; `null` é 422."""

    model_config = ConfigDict(extra="forbid")

    nome: str = omitido(min_length=1, max_length=120)
    ativa: bool = omitido()


class CategoriaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nome: str
    ativa: bool
    created_at: datetime


class DespesaCreate(BaseModel):
    """Lança despesa; nasce `prevista` (CA-F06.5). `obra_fase_id` é obrigatório (RN-F02)."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    categoria_id: UUID
    fornecedor_nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(min_length=1, max_length=500)
    valor: DinheiroPositivo
    data_competencia: date
    vencimento: date
    documento_id: UUID | None = None


class DespesaUpdate(BaseModel):
    """Edição parcial. Status não é editável aqui (use pagar/estornar/DELETE).

    Campo omitido não muda; campo NOT NULL com `null` explícito é 422. Só
    `documento_id` aceita `null`. Leia com `model_dump(exclude_unset=True)`."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID = omitido()
    categoria_id: UUID = omitido()
    fornecedor_nome: str = omitido(min_length=1, max_length=200)
    descricao: str = omitido(min_length=1, max_length=500)
    valor: DinheiroPositivo = omitido()
    data_competencia: date = omitido()
    vencimento: date = omitido()
    # Único campo que aceita `null`: desvincula a NF (CA-F07.3).
    documento_id: UUID | None = None


class DespesaPagar(BaseModel):
    """Registra pagamento (CA-F09.1); o valor pago é o do título."""

    model_config = ConfigDict(extra="forbid")

    data_pagamento: date


class DespesaParceladaCreate(BaseModel):
    """Gera N títulos numa transação (RN-F08). `valor` é o total; o resíduo de
    arredondamento vai na última parcela."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    categoria_id: UUID
    fornecedor_nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(min_length=1, max_length=500)
    valor: DinheiroPositivo
    data_competencia: date
    numero_parcelas: int = Field(ge=2, le=120)
    primeiro_vencimento: date
    documento_id: UUID | None = None


class DespesaOut(BaseModel):
    """`fase_descricao` e `categoria_nome` vêm de `obra_fase` e `categoria_financeira`
    (CA-F10.1); `categoria_id` é NOT NULL (Dicionário §4.3), logo o nome também."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    obra_fase_id: UUID
    fase_descricao: str
    categoria_id: UUID
    categoria_nome: str
    fornecedor_nome: str
    fornecedor_id: UUID | None
    descricao: str
    valor: DinheiroOut
    data_competencia: date
    vencimento: date
    status: DespesaStatus
    data_pagamento: date | None
    documento_id: UUID | None
    grupo_parcelas_id: UUID | None
    parcela_num: int | None
    parcela_total: int | None
    created_at: datetime
    created_by: UUID | None


class DespesaPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DespesaOut]
    next_cursor: str | None


class DespesaParceladaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grupo_parcelas_id: UUID
    parcelas: list[DespesaOut]


class FaseObraOut(BaseModel):
    """Fase da obra para o seletor de lançamento (RN-F03). Inclui as inativas."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    codigo: str
    descricao: str
    ativa: bool
