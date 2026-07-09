"""Schemas Pydantic v2 do CRUD de tickets (B4.2, US-08) — fonte da verdade do
contrato. `extra='forbid'`: campo desconhecido é 422.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TicketStatus = Literal["aberto", "andamento", "resolvido", "fechado"]

# docs/SPRINTS.md B4.2: descrição com até 5KB.
MAX_DESCRICAO = 5000


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = Field(default=None, max_length=MAX_DESCRICAO)


class TicketStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus


class TicketOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    titulo: str
    descricao: str | None
    status: TicketStatus
    created_by: UUID | None
    created_at: datetime


class TicketPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TicketOut]
    next_cursor: str | None
