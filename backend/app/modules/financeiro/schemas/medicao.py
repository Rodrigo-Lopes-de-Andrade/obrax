"""Schemas de medição e recebimento (ESPEC §6.1-6.2, Dicionário §4.7-4.9).

Percentuais são `Decimal` **como fração** (0.20 = 20%) e **acumulados** desde o
início da obra (RN-F05), não o avanço do período.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.financeiro.schemas._types import (
    DinheiroOut,
    Fracao,
    FracaoOut,
    MedicaoStatus,
    RecebimentoStatus,
)


class MedicaoCreate(BaseModel):
    """Cria rascunho para um período do cronograma (CA-F03.1)."""

    model_config = ConfigDict(extra="forbid")

    periodo_id: UUID
    observacao: str | None = Field(default=None, max_length=2000)


class MedicaoItemIn(BaseModel):
    """`percentual_acumulado` é fração acumulada (0.20 = 20%), RN-F05."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    percentual_acumulado: Fracao


class MedicaoItensPut(BaseModel):
    """Substitui o conjunto de itens do rascunho."""

    model_config = ConfigDict(extra="forbid")

    itens: list[MedicaoItemIn] = Field(min_length=1)


class MedicaoAprovar(BaseModel):
    """Payload de aprovação. `vencimento` do título a receber é informado aqui
    (Dicionário §4.9); pode faltar numa obra sem `valor_contrato` (CA-F04.7)."""

    model_config = ConfigDict(extra="forbid")

    vencimento: date | None = None


class MedicaoItemOut(BaseModel):
    """`percentual_acumulado` é fração (0.20 = 20%)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_fase_id: UUID
    percentual_acumulado: FracaoOut
    valor_medido: DinheiroOut


class MedicaoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    cronograma_id: UUID
    periodo_id: UUID
    status: MedicaoStatus
    aprovada_em: datetime | None
    aprovada_por: UUID | None
    valor_liberado: DinheiroOut | None
    observacao: str | None
    created_at: datetime
    created_by: UUID | None


class MedicaoDetail(MedicaoOut):
    """Medição com itens (percentuais como fração acumulada)."""

    itens: list[MedicaoItemOut]


class MedicaoPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MedicaoOut]
    next_cursor: str | None


class RecebimentoOut(BaseModel):
    """`obra_nome` vem de `obras`; `medicao_numero` é o `numero` do período da
    medição (`cronograma_periodo.numero`, INTEGER, a partir de 1): `medicao` não tem
    coluna própria de número (Dicionário §4.5/§4.7). CA-F10.1."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    obra_nome: str
    medicao_id: UUID
    medicao_numero: int
    valor: DinheiroOut
    vencimento: date
    status: RecebimentoStatus
    data_recebimento: date | None
    created_at: datetime


class RecebimentoPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RecebimentoOut]
    next_cursor: str | None


class RecebimentoReceber(BaseModel):
    """Marca o título como recebido (CA-F10.2)."""

    model_config = ConfigDict(extra="forbid")

    data_recebimento: date


class MedicaoAprovadaOut(BaseModel):
    """Resultado da aprovação. `recebimento` é nulo e `aviso` preenchido quando a
    obra não tem `valor_contrato` (CA-F04.7)."""

    model_config = ConfigDict(extra="forbid")

    medicao: MedicaoDetail
    recebimento: RecebimentoOut | None
    aviso: str | None
