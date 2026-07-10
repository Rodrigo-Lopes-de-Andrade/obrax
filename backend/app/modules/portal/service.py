"""Regras de negócio do portal do cliente (B9.2, US-19).

Duas superfícies com origens de tenant distintas:
- `mint_portal_link` roda sob `get_db` (admin autenticado, RLS pelo JWT de
  acesso): valida a obra do tenant e emite o token do portal (escopo = 1 obra).
- `get_portal_obra` roda sob `get_portal_db` (RLS pelo token do portal): lê o
  andamento da obra, os documentos `visivel_cliente=true` e as fotos
  sincronizadas — nada financeiro (SPRINTS B9.2).

`storage_path` guarda só a chave; as `download_url` são assinadas sob demanda
(docs/CLAUDE.md — nunca persistir URL).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_portal_token
from app.integrations.storage import StorageClient

# TTL das URLs de download do portal — curto, re-assinadas a cada leitura.
_DOWNLOAD_TTL_SECONDS = 900

_OBRA_NAO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada"
)


def mint_portal_link(session: Session, *, company_id: str, obra_id: uuid.UUID) -> dict[str, Any]:
    """Emite o link do portal para uma obra do tenant (admin). 404 se a obra
    não existe/for de outro tenant (escondida pela RLS)."""
    row = (
        session.execute(
            text("SELECT cliente_id FROM obras WHERE id = :id AND deleted_at IS NULL"),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _OBRA_NAO_ENCONTRADA

    issued = create_portal_token(
        company_id=uuid.UUID(company_id),
        obra_id=obra_id,
        cliente_id=row["cliente_id"],
    )
    return {
        "token": issued.token,
        "url": f"/obra/{issued.token}",
        "expires_at": issued.expires_at,
    }


def _sign(storage: StorageClient, key: str | None) -> str | None:
    return storage.presigned_get_url(key=key, expires_in=_DOWNLOAD_TTL_SECONDS) if key else None


def get_portal_obra(
    session: Session, storage: StorageClient, *, obra_id: uuid.UUID
) -> dict[str, Any]:
    """Timeline read-only da obra: dados de andamento + docs visíveis + fotos."""
    obra = (
        session.execute(
            text(
                "SELECT o.id, o.codigo, o.nome, o.status, o.data_inicio, o.data_prevista_fim, "
                "       c.razao_social AS construtora "
                "FROM obras o JOIN companies c ON c.id = o.company_id "
                "WHERE o.id = :id AND o.deleted_at IS NULL"
            ),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if obra is None:
        raise _OBRA_NAO_ENCONTRADA

    # Só documentos marcados visíveis ao cliente e já confirmados (com objeto no
    # storage). Ordem cronológica reversa (id v7 ~ tempo).
    documentos = [
        {
            "id": d["id"],
            "nome": d["nome"],
            "tipo": d["tipo"],
            "categoria": d["categoria"],
            "created_at": d["created_at"],
            "download_url": _sign(storage, d["storage_path"]),
        }
        for d in session.execute(
            text(
                "SELECT id, nome, tipo, categoria, created_at, storage_path FROM documento "
                "WHERE obra_id = :obra_id AND visivel_cliente = true "
                "  AND deleted_at IS NULL AND storage_path IS NOT NULL "
                "ORDER BY id DESC"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .all()
    ]

    fotos = [
        {
            "id": f["id"],
            "captured_at": f["captured_at"],
            "download_url": _sign(storage, f["storage_path"]),
        }
        for f in session.execute(
            text(
                "SELECT id, captured_at, storage_path FROM photo "
                "WHERE obra_id = :obra_id AND sync_status = 'sincronizado' "
                "  AND deleted_at IS NULL "
                "ORDER BY id DESC"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .all()
    ]

    return {
        "id": obra["id"],
        "codigo": obra["codigo"],
        "nome": obra["nome"],
        "status": obra["status"],
        "data_inicio": obra["data_inicio"],
        "data_prevista_fim": obra["data_prevista_fim"],
        "construtora": obra["construtora"],
        "documentos": documentos,
        "fotos": fotos,
    }
