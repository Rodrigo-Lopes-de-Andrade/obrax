"""Schemas do portal do cliente (B9.2, US-19). `extra='forbid'` em todos.

Superfície deliberadamente enxuta e read-only: só o que o cliente pode ver
(SPRINTS B9.2 "dados apenas visíveis, sem dados financeiro internos"). Por isso
`PortalObra` NÃO expõe `valor_contrato`, custos, markup ou qualquer número de
orçamento — só o andamento da obra, os documentos marcados `visivel_cliente` e
a galeria de fotos sincronizadas.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PortalLinkOut(BaseModel):
    """Resultado do `POST /obras/{id}/portal-link` (admin): o link a enviar ao
    cliente. `url` é relativa (o front compõe o host)."""

    model_config = ConfigDict(extra="forbid")

    token: str
    url: str
    expires_at: datetime


class PortalDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nome: str
    tipo: str
    categoria: str | None
    created_at: datetime
    # URL de download assinada (TTL curto), gerada sob demanda.
    download_url: str | None


class PortalFoto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    captured_at: datetime
    download_url: str | None


class PortalObra(BaseModel):
    """Timeline read-only da obra para o cliente — sem números financeiros."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    codigo: str
    nome: str
    status: str
    data_inicio: date | None
    data_prevista_fim: date | None
    # Razão social da construtora (branding do portal, F9.1).
    construtora: str
    documentos: list[PortalDocumento]
    fotos: list[PortalFoto]
