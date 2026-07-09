"""Schemas Pydantic v2 do CRUD de tickets (B4.2, US-08) — fonte da verdade do
contrato. `extra='forbid'`: campo desconhecido é 422.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TicketStatus = Literal["aberto", "andamento", "resolvido", "fechado"]

# docs/SPRINTS.md B4.2: descrição com até 5KB.
MAX_DESCRICAO = 5000
# docs/SPRINTS.md B4.3: mensagem com texto + até 5 anexos.
MAX_CONTENT = 5000
MAX_ATTACHMENTS = 5
MAX_PATH_LEN = 512


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


class MensagemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=MAX_CONTENT)
    attachment_paths: list[str] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)

    @field_validator("attachment_paths")
    @classmethod
    def _paths_sao_do_storage(cls, paths: list[str]) -> list[str]:
        # Anexos são caminhos no bucket (nunca URLs — docs/CLAUDE.md). A URL é
        # (re)assinada na leitura, como em documentos.
        for p in paths:
            if not p or len(p) > MAX_PATH_LEN:
                raise ValueError("anexo inválido: caminho vazio ou grande demais")
            if "://" in p:
                raise ValueError("anexo deve ser um caminho no storage, não uma URL")
        return paths


class MensagemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    ticket_id: UUID
    author_id: UUID | None
    content: str
    attachment_paths: list[str]
    created_at: datetime


class MensagemPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MensagemOut]
    next_cursor: str | None
