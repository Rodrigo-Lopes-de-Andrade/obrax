"""Schemas dos pedidos LGPD (B9.4 export / B9.5 delete). `extra='forbid'`."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

LgpdRequestType = Literal["export", "delete"]


class LgpdRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: LgpdRequestType
    # Titular do pedido. Obrigatório para `delete` (a quem esquecer);
    # ignorado no `export` (exporta o tenant inteiro). Validado no service.
    cliente_id: UUID | None = None


class LgpdRequestOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_type: str
    status: str
    cliente_id: UUID | None
    created_at: datetime
    expires_at: datetime | None
    processed_at: datetime | None
    # URL assinada do ZIP, presente só quando o pedido acabou de ser criado ou
    # no endpoint de download (nunca persistida — assinada sob demanda).
    download_url: str | None = None


class LgpdRequestPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LgpdRequestOut]
    next_cursor: str | None


class LgpdDownloadOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    download_url: str
    expires_at: datetime
