"""Schemas Pydantic v2 do Módulo 3 (contrato do webhook + painel IA).

Espelha `frontend/lib/api/types.ts` (AiRole, AgentChatMessage, AgentInteraction,
AiPermission, CopilotSuggestion, IaInsights). `extra='forbid'` (docs/CLAUDE.md).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AiRole = Literal["consultor", "solicitador", "aprovador"]
AgentInteractionStatus = Literal["ok", "erro", "revertido"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _OrmBase(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ── Webhook Uazapi (B10.1) ─────────────────────────────────────────────────
class UazapiWebhookIn(_Base):
    """Corpo mínimo do webhook do Uazapi. `message_id` é a chave de idempotência;
    `from_number` o remetente; `text` o conteúdo. Campos extras do provedor são
    ignorados na borda (o router lê o corpo cru para o HMAC antes de validar)."""

    message_id: str = Field(min_length=1)
    from_number: str = Field(min_length=1)
    text: str = Field(min_length=1)


class WebhookAck(_Base):
    status: Literal["queued", "duplicate", "ignored"]
    message_id: str


# ── Assistente (F10.1) ────────────────────────────────────────────────────
class ChatMessageIn(_Base):
    content: str = Field(min_length=1)


class ChatMessageOut(_Base):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


# ── Auditoria (F10.2 / B10.6) ─────────────────────────────────────────────
class InteractionOut(_Base):
    id: UUID
    whatsapp_number: str
    command: str
    intent: str | None
    agent: str | None
    action: str | None
    result: str | None
    status: AgentInteractionStatus
    cost_cents: int
    obra_id: UUID | None
    obra_codigo: str | None
    reverted_at: datetime | None
    created_at: datetime


class InteractionPage(_Base):
    items: list[InteractionOut]
    next_cursor: str | None


# ── Permissões (F10.3 / B10.7) ────────────────────────────────────────────
class PermissionCreate(_Base):
    whatsapp_number: str = Field(min_length=3)
    role: AiRole
    daily_limit_cents: int = Field(default=0, ge=0)
    monthly_limit_cents: int = Field(default=0, ge=0)


class PermissionOut(_OrmBase):
    id: UUID
    whatsapp_number: str
    role: AiRole
    daily_limit_cents: int
    monthly_limit_cents: int
    created_at: datetime


class PermissionPage(_Base):
    items: list[PermissionOut]
    next_cursor: str | None


# ── Copilot (F10.4) ───────────────────────────────────────────────────────
class CopilotIn(_Base):
    descricao: str = Field(min_length=1)


class CopilotSuggestionOut(_Base):
    descricao: str
    unidade: str
    # Decimal serializado como string (nunca float em quantidade — CLAUDE.md).
    quantidade: str


# ── Insights (F10.5) ──────────────────────────────────────────────────────
class InsightsOut(_Base):
    acoes_ultima_semana: int
    economia_tempo_min: int
    taxa_sucesso: float
    ultimas_acoes: list[InteractionOut]
