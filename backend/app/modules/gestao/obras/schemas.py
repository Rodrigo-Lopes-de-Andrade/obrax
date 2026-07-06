"""Schemas Pydantic v2 do CRUD de obras (B2.3) — fonte da verdade do contrato.
`extra='forbid'` em todos: campo desconhecido é 422.

`valor_contrato` é `Decimal` (NUMERIC(18,2) no banco) — float é proibido em
valores financeiros (docs/CLAUDE.md > Precisão financeira).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.gestao.obras.validators import validate_date_order

ObraStatus = Literal["planejamento", "execucao", "pausada", "concluida", "cancelada"]


class ObraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: UUID
    codigo: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    status: ObraStatus = "planejamento"
    data_inicio: date | None = None
    data_prevista_fim: date | None = None
    data_real_fim: date | None = None
    valor_contrato: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def _check_dates(self) -> ObraCreate:
        # Levanta ValueError -> 422 se data_prevista_fim < data_inicio.
        validate_date_order(self.data_inicio, self.data_prevista_fim)
        return self


class ObraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `cliente_id` é imutável após a criação (âncora do registro) — não exposto
    # no PATCH. A validação da ordem das datas contra os valores efetivos é
    # feita no service, que conhece o registro atual.
    codigo: str | None = Field(default=None, min_length=1)
    nome: str | None = Field(default=None, min_length=1)
    status: ObraStatus | None = None
    data_inicio: date | None = None
    data_prevista_fim: date | None = None
    data_real_fim: date | None = None
    valor_contrato: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)


class ObraOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    cliente_id: UUID
    status: ObraStatus
    codigo: str
    nome: str
    data_inicio: date | None
    data_prevista_fim: date | None
    data_real_fim: date | None
    valor_contrato: Decimal | None
    created_at: datetime


class ObraPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ObraOut]
    # Cursor para a próxima página (o `id` do último item); None = fim.
    next_cursor: str | None
