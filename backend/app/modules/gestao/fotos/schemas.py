"""Schemas Pydantic v2 das fotos de campo (B8.2/B8.3) — fonte da verdade do
contrato. `extra='forbid'` em todos: campo desconhecido é 422.

Fluxo em duas etapas (docs/CLAUDE.md § Contrato / ESPEC § 7), igual a documento:
`POST /photos/sync` cria a linha pendente e devolve uma URL de `PUT` assinada; o
cliente sobe o arquivo direto no storage; `POST /photos/{id}/confirm` valida
tamanho + SHA-256 e marca `sincronizado`. O `client_photo_id` (chave de
idempotência do aparelho) NÃO vem no corpo: viaja no header `Idempotency-Key`
(obrigatório neste endpoint). O `sha256` é calculado no cliente antes do upload
e serve para dedup por conteúdo + checagem de integridade no confirm.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# B8.3: foto final comprimida no cliente cabe em 2 MB (browser-image-compression).
MAX_PHOTO_BYTES = 2 * 1024 * 1024


class PhotoSyncCreate(BaseModel):
    """Corpo do `POST /photos/sync`. `client_photo_id` vem do header
    `Idempotency-Key`, não daqui."""

    model_config = ConfigDict(extra="forbid")

    obra_id: UUID
    # SHA-256 hex (64 chars) do conteúdo, calculado no cliente. Normalizado p/
    # minúsculo — a comparação de dedup/integridade é por string exata.
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0, le=MAX_PHOTO_BYTES)
    # Relógio do aparelho no momento da captura (informativo; o servidor carimba
    # `synced_at` no confirm).
    captured_at: datetime

    @field_validator("sha256")
    @classmethod
    def _sha256_hex(cls, v: str) -> str:
        v = v.lower()
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError("sha256 deve ser hexadecimal (64 chars)")
        return v


class PhotoSyncOut(BaseModel):
    """Resposta do sync: a URL assinada que o cliente usa no `PUT` direto."""

    model_config = ConfigDict(extra="forbid")

    photo_id: UUID
    upload_url: str
    method: str
    expires_in: int


class PhotoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    ocorrencia_id: UUID | None
    client_photo_id: UUID
    sha256: str
    size_bytes: int
    sync_status: str
    captured_at: datetime
    synced_at: datetime | None
    created_at: datetime
    # URL de download assinada (curta), gerada sob demanda; `None` enquanto a
    # foto ainda não foi confirmada (não há objeto no bucket).
    download_url: str | None


class PhotoPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PhotoOut]
    # Cursor para a próxima página (o `id` do último item); None = fim.
    next_cursor: str | None
