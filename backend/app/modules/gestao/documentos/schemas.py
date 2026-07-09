"""Schemas Pydantic v2 do upload de documentos (B3.2) — fonte da verdade do
contrato. `extra='forbid'` em todos: campo desconhecido é 422.

Fluxo em duas etapas (docs/ESPEC.md § 7): `POST /obras/{id}/documentos` cria a
linha pendente e devolve uma URL de `PUT` assinada; o cliente sobe o arquivo
direto no storage; `POST /documentos/{id}/confirm` valida e marca como
sincronizado. O `sha256` é calculado no cliente (antes do upload) e serve tanto
para dedup `(obra_id, sha256)` quanto para a checagem de integridade.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DocumentoTipo = Literal["projeto", "contrato", "nota_fiscal", "foto", "outro"]

# docs/ESPEC.md § 7 / SPRINTS B3.2: upload direto até <50MB.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class DocumentoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=512)
    tipo: DocumentoTipo
    # SHA-256 hex (64 chars) do conteúdo, calculado no cliente. Normalizado p/
    # minúsculo — a comparação de dedup é por string exata.
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0, le=MAX_UPLOAD_BYTES)
    categoria: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("sha256")
    @classmethod
    def _sha256_hex(cls, v: str) -> str:
        v = v.lower()
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError("sha256 deve ser hexadecimal (64 chars)")
        return v


class DocumentoUploadOut(BaseModel):
    """Resposta do create: a URL assinada que o cliente usa no `PUT` direto."""

    model_config = ConfigDict(extra="forbid")

    documento_id: UUID
    upload_url: str
    method: str
    expires_in: int


class DocumentoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    nome: str
    tipo: DocumentoTipo
    categoria: str | None
    visivel_cliente: bool
    size_bytes: int | None
    sha256: str | None
    # `true` quando o upload foi confirmado (storage_path preenchido no confirm).
    confirmed: bool
    created_at: datetime
