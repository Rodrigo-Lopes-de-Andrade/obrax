"""Schemas Pydantic v2 das ocorrências de campo (B8.4, US-18) — fonte da verdade
do contrato. `extra='forbid'` em todos: campo desconhecido é 422.

Uma ocorrência registra um problema em campo (ex.: "Infiltração na laje") com
foto obrigatória (evidência) e GPS opcional. As fotos são capturadas/enviadas
antes pelo fluxo de sync (`/photos/sync` → `/confirm`) e vinculadas aqui por id
(`photo_ids`). O status é tri-... na verdade bi-estado: aberto/resolvido.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OcorrenciaStatus = Literal["aberto", "resolvido"]


class OcorrenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = Field(default=None, max_length=5000)
    # GPS opcional (geolocation do navegador, se autorizado). Coordenadas em
    # graus decimais — não são valores financeiros, então `float` serve.
    gps_lat: float | None = Field(default=None, ge=-90, le=90)
    gps_lng: float | None = Field(default=None, ge=-180, le=180)
    # Foto obrigatória (US-18): ao menos uma evidência já sincronizada.
    photo_ids: list[UUID] = Field(min_length=1)


class OcorrenciaUpdate(BaseModel):
    """PATCH parcial — hoje só o status (aberto/resolvido). Corpo vazio é 422."""

    model_config = ConfigDict(extra="forbid")

    status: OcorrenciaStatus | None = None


class OcorrenciaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    titulo: str
    descricao: str | None
    status: OcorrenciaStatus
    gps_lat: float | None
    gps_lng: float | None
    photo_ids: list[UUID]
    created_at: datetime


class OcorrenciaPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OcorrenciaOut]
    # Cursor para a próxima página (o `id` do último item); None = fim.
    next_cursor: str | None
