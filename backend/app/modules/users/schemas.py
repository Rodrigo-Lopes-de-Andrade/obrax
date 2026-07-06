"""Schemas Pydantic v2 do módulo de usuários (convites, B1.5 / US-19 prep)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

# `ai` (agente WhatsApp) não é um papel convidável por este fluxo — é
# atribuído via `PUT /api/v1/agentes/permissoes` (Sprint 10, fora de escopo).
InvitableRole = Literal["owner", "admin", "gestor", "orcamentista", "financeiro", "viewer", "campo"]


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role: InvitableRole


class InviteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role: InvitableRole
    expires_at: datetime
    # Premissa (ver relatório do agente): sem job de e-mail (Arq só chega na
    # Sprint 4 — `email.send`), o token é devolvido diretamente na resposta
    # para permitir testar o fluxo ponta a ponta nesta sprint. Isso é
    # temporário: quando `jobs/email.send` existir, o token deve parar de
    # voltar no corpo da resposta e ser enviado apenas por e-mail.
    invite_token: str


class InviteListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role: InvitableRole
    expires_at: datetime
    accepted_at: datetime | None
