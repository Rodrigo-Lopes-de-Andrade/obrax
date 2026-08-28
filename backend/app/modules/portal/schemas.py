"""Schemas do portal do cliente (B9.2, US-19). `extra='forbid'` em todos.

Superfície deliberadamente enxuta e read-only: só o que o cliente pode ver
(SPRINTS B9.2 "dados apenas visíveis, sem dados financeiro internos"). Por isso
`PortalObra` NÃO expõe `valor_contrato`, custos, markup ou qualquer número de
orçamento — só o andamento da obra, os documentos marcados `visivel_cliente` e
a galeria de fotos sincronizadas.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class PortalOrcamento(BaseModel):
    """Orçamento que o cliente vê para aprovar (B9.3). Expõe só o preço final
    (`preco_venda`) — nunca custo direto/markup/margem internos."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    titulo: str
    status: str
    preco_venda: Decimal
    # URL assinada do PDF timbrado (viewer do portal); None se ainda não gerado.
    pdf_url: str | None
    # Decisão já registrada (idempotência / reexibição), se houver.
    decisao: str | None
    decidido_em: datetime | None


class PortalAprovacaoIn(BaseModel):
    """Corpo de `POST /portal/orcamentos/{token}/aprovar|rejeitar` (B9.3)."""

    model_config = ConfigDict(extra="forbid")

    comentario: str | None = Field(default=None, max_length=5000)
    # Nome digitado pelo cliente que assina (opcional).
    assinado_por: str | None = Field(default=None, max_length=200)
    # Imagem da assinatura como data URL base64 (data:image/png;base64,...),
    # opcional (F9.3: "assinatura digital opcional"). Guardada como evidência.
    assinatura: str | None = Field(default=None, max_length=2_000_000)


class PortalMensagem(BaseModel):
    """Mensagem do chat de um chamado, na visão do cliente (US-19). Espelha
    `MensagemOut` do admin; `author_id` NULL = mensagem do próprio cliente."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    ticket_id: UUID
    author_id: UUID | None
    content: str
    attachment_paths: list[str]
    created_at: datetime


class PortalTicket(BaseModel):
    """Chamado da obra com o histórico de mensagens (read-only + responder)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    titulo: str
    status: str
    created_at: datetime
    mensagens: list[PortalMensagem]


class PortalMensagemIn(BaseModel):
    """Corpo de `POST /portal/tickets/{token}/{ticket_id}/mensagens` (US-19).
    O cliente só envia texto — sem anexos (não tem acesso ao storage)."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)
