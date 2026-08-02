"""Schemas Pydantic v2 do módulo de autenticação — fonte da verdade do
contrato de API (docs/CLAUDE.md > Stack > Backend). `extra='forbid'` em
todos os modelos: payload com campo desconhecido é 422, não ignorado.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    """Usuário autenticado da sessão (GET /auth/me). `role` é do vínculo do JWT."""

    id: str
    nome: str
    email: str
    role: str


class MagicConsumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str


class AcceptInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    nome: str = Field(min_length=1)
    password: str = Field(min_length=8)
