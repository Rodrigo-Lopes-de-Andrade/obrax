"""Schemas Pydantic v2 do CRUD de equipe (B3.6) — fonte da verdade do contrato.
`extra='forbid'`: campo desconhecido é 422.

`MembroOut` traz `nome`/`email` do usuário (join em `users`) para a DataTable de
equipes (F3.4) não precisar de um segundo request.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MembroCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    papel: str = Field(min_length=1, max_length=64)


class MembroOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    nome: str
    email: str
    papel: str
    created_at: datetime


class MembroPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MembroOut]
    # Cursor para a próxima página (o `id` do último vínculo); None = fim.
    next_cursor: str | None
