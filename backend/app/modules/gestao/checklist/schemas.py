"""Schemas do checklist de campo (B7.2, US-16). `extra='forbid'`: campo
desconhecido é 422.

O app mobile opera offline e sincroniza os toggles depois (Dexie queue). O PATCH
é parcial (`exclude_unset`): o toggle envia só `completed`; a edição só `titulo`.
Quando `completed` vira `true`, o servidor carimba `completed_at` (não vem do
cliente, cujo relógio é pouco confiável).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChecklistItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)
    # Posição opcional; se ausente, o item vai para o fim da lista.
    sort_order: int | None = Field(default=None, ge=0)


class ChecklistItemUpdate(BaseModel):
    """PATCH parcial — só os campos enviados mudam. Toggle = `{completed: bool}`."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    titulo: str
    completed: bool
    completed_at: datetime | None
    sort_order: int
    created_at: datetime


class ChecklistPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ChecklistItemOut]
    # Cursor para a próxima página (o `id` do último item); None = fim.
    next_cursor: str | None
