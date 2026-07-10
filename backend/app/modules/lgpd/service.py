"""Regras de negócio dos pedidos LGPD (B9.4 export; B9.5 completa o delete).

Roda sob `get_db` (role `app_user`, RLS ativa) — as queries já saem escopadas ao
tenant. O export é síncrono (sem fila): monta o ZIP, sobe no storage guardando
só a chave (`payload_path`) e grava o pedido já `concluido` com TTL de 7 dias
(`expires_at`). O download assina a URL sob demanda enquanto dentro da janela.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.storage import StorageClient
from app.modules.lgpd.export import build_export_zip
from app.modules.lgpd.schemas import LgpdRequestCreate

# URL de download re-assinada a cada acesso (curta); a janela de vida do arquivo
# é `expires_at` = created_at + 7 dias (SPRINTS B9.4 "link 7 dias").
_DOWNLOAD_TTL_SECONDS = 300

_COLUMNS = "id, request_type, status, cliente_id, created_at, expires_at, processed_at"

_NAO_ENCONTRADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="pedido LGPD não encontrado"
)


def _export_key(company_id: str) -> str:
    return f"{company_id}/lgpd-exports/{uuid.uuid4()}.zip"


def create_export(
    session: Session, storage: StorageClient, *, company_id: str, requested_by: uuid.UUID
) -> dict[str, Any]:
    """Monta e sobe o ZIP do tenant, grava o pedido `concluido` (TTL 7d) e
    devolve com a URL de download já assinada."""
    zip_bytes = build_export_zip(session)
    key = _export_key(company_id)
    storage.put_object(key=key, body=zip_bytes, content_type="application/zip")

    row = (
        session.execute(
            text(
                "INSERT INTO lgpd_request "
                "(company_id, request_type, status, requested_by, payload_path, "
                " expires_at, processed_at) "
                "VALUES (:c, 'export', 'concluido', :rb, :key, "
                " now() + interval '7 days', now()) "
                f"RETURNING {_COLUMNS}"
            ),
            {"c": company_id, "rb": requested_by, "key": key},
        )
        .mappings()
        .one()
    )
    out = dict(row)
    out["download_url"] = storage.presigned_get_url(key=key, expires_in=_DOWNLOAD_TTL_SECONDS)
    return out


def create_request(
    session: Session,
    storage: StorageClient,
    *,
    company_id: str,
    requested_by: uuid.UUID,
    payload: LgpdRequestCreate,
) -> dict[str, Any]:
    """Dispatcher do POST /lgpd/requests. B9.4 cobre `export`; `delete` é
    implementado em B9.5 (right to be forgotten)."""
    if payload.request_type == "export":
        return create_export(session, storage, company_id=company_id, requested_by=requested_by)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="tipo de pedido LGPD não suportado",
    )


def list_requests(
    session: Session, *, cursor: str | None, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    if cursor is not None:
        try:
            uuid.UUID(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cursor inválido"
            ) from exc

    rows = (
        session.execute(
            text(
                f"SELECT {_COLUMNS} FROM lgpd_request "
                "WHERE (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "ORDER BY id DESC LIMIT :limit_plus_one"
            ),
            {"cursor": cursor, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def get_download(session: Session, storage: StorageClient, *, request_id: uuid.UUID) -> dict[str, Any]:
    """URL de download da exportação, se ainda válida. 404 inexistente, 409 se
    não concluída, 410 se o link já expirou (>7 dias)."""
    row = (
        session.execute(
            text(
                "SELECT status, payload_path, expires_at FROM lgpd_request WHERE id = :id"
            ),
            {"id": request_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NAO_ENCONTRADO
    if row["status"] != "concluido" or not row["payload_path"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="exportação ainda não disponível"
        )
    if row["expires_at"] is not None and row["expires_at"] < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="link de exportação expirado")
    return {
        "download_url": storage.presigned_get_url(
            key=row["payload_path"], expires_in=_DOWNLOAD_TTL_SECONDS
        ),
        "expires_at": row["expires_at"],
    }
