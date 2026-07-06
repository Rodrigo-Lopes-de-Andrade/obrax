"""Schemas Pydantic v2 do CRUD de clientes (B2.2) — fonte da verdade do
contrato. `extra='forbid'` em todos: campo desconhecido é 422.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.gestao.clientes.validators import validate_documento

TipoPessoa = Literal["PF", "PJ"]


class ClienteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_pessoa: TipoPessoa
    documento: str
    nome: str = Field(min_length=1)
    telefone: str | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def _normalize_documento(self) -> ClienteCreate:
        # Levanta ValueError -> 422 se CPF/CNPJ inválido; guarda só os dígitos.
        self.documento = validate_documento(self.tipo_pessoa, self.documento)
        return self


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Todos opcionais (PATCH). A validação de `documento` contra o
    # `tipo_pessoa` efetivo é feita no service, que conhece o registro atual.
    tipo_pessoa: TipoPessoa | None = None
    documento: str | None = None
    nome: str | None = Field(default=None, min_length=1)
    telefone: str | None = None
    email: EmailStr | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tipo_pessoa: TipoPessoa
    documento: str
    nome: str
    telefone: str | None
    email: EmailStr | None
    created_at: datetime


class ClientePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ClienteOut]
    # Cursor para a próxima página (o `id` do último item); None = fim.
    next_cursor: str | None
