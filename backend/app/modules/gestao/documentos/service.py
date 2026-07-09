"""Regras de negócio do upload de documentos (B3.2).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. A `obra_id` é validada contra a RLS antes do INSERT (FK
bypassa row-level security, como em obras→clientes) para não permitir anexar
documento numa obra de outro tenant.

Estado do documento sem coluna extra (o schema do B3.1 não tem `sync_status`):
`storage_path IS NULL` = pendente (criado, upload ainda não confirmado);
preenchido no confirm = sincronizado. A chave no bucket é determinística
(`company_id/obra_id/documento_id`), computável no create e recomputável no
confirm sem persistir a URL assinada.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.storage import StorageClient
from app.modules.gestao.documentos.schemas import DocumentoCreate, DocumentoUpdate

# `storage_path IS NOT NULL AS confirmed`: expõe o estado sincronizado sem
# vazar o caminho interno no bucket.
_OUT_COLUMNS = (
    "id, obra_id, nome, tipo, categoria, visivel_cliente, size_bytes, sha256, "
    "(storage_path IS NOT NULL) AS confirmed, created_at"
)
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documento não encontrado")
_OBRA_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="obra não encontrada"
)
_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="documento duplicado: mesmo conteúdo (sha256) já enviado nesta obra",
)


def _storage_key(company_id: str, obra_id: uuid.UUID, documento_id: uuid.UUID) -> str:
    return f"{company_id}/{obra_id}/{documento_id}"


def _assert_obra_do_tenant(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _OBRA_INVALIDA


def _get_out(session: Session, documento_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_OUT_COLUMNS} FROM documento WHERE id = :id AND deleted_at IS NULL"),
            {"id": documento_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def create_upload(
    session: Session,
    storage: StorageClient,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    payload: DocumentoCreate,
) -> dict[str, Any]:
    _assert_obra_do_tenant(session, obra_id)

    # Pré-checagem de dedup (mensagem clara); a UNIQUE (obra_id, sha256) é o
    # backstop para corrida/soft-delete — a IntegrityError também vira 409.
    existing = session.execute(
        text(
            "SELECT 1 FROM documento "
            "WHERE obra_id = :obra_id AND sha256 = :sha256 AND deleted_at IS NULL"
        ),
        {"obra_id": obra_id, "sha256": payload.sha256},
    ).first()
    if existing is not None:
        raise _DUPLICADO

    try:
        documento_id = session.execute(
            text(
                "INSERT INTO documento "
                "(company_id, obra_id, nome, tipo, sha256, size_bytes, categoria, uploaded_by) "
                "VALUES (:company_id, :obra_id, :nome, CAST(:tipo AS documento_tipo), "
                " :sha256, :size_bytes, :categoria, :uploaded_by) "
                "RETURNING id"
            ),
            {
                "company_id": company_id,
                "obra_id": obra_id,
                "nome": payload.nome,
                "tipo": payload.tipo,
                "sha256": payload.sha256,
                "size_bytes": payload.size_bytes,
                "categoria": payload.categoria,
                "uploaded_by": uploaded_by,
            },
        ).scalar_one()
    except IntegrityError as exc:
        session.rollback()
        raise _DUPLICADO from exc

    key = _storage_key(company_id, obra_id, documento_id)
    presigned = storage.presigned_put_url(key=key)
    return {
        "documento_id": documento_id,
        "upload_url": presigned.url,
        "method": presigned.method,
        "expires_in": presigned.expires_in,
    }


def confirm_upload(
    session: Session,
    storage: StorageClient,
    *,
    documento_id: uuid.UUID,
) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                "SELECT company_id, obra_id, size_bytes, storage_path FROM documento "
                "WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": documento_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND

    # Idempotente: reconfirmar um documento já sincronizado devolve o estado
    # atual (o cliente pode reenviar o confirm após um timeout de rede).
    if row["storage_path"] is not None:
        return _get_out(session, documento_id)

    key = _storage_key(str(row["company_id"]), row["obra_id"], documento_id)
    stat = storage.stat(key=key)
    if stat is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="arquivo não encontrado no storage — upload não concluído",
        )
    if stat.size_bytes != row["size_bytes"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tamanho do arquivo diverge do informado no upload",
        )

    row = (
        session.execute(
            text(
                f"UPDATE documento SET storage_path = :key "
                "WHERE id = :id AND deleted_at IS NULL "
                f"RETURNING {_OUT_COLUMNS}"
            ),
            {"key": key, "id": documento_id},
        )
        .mappings()
        .one()
    )
    return dict(row)


def list_documentos(
    session: Session,
    *,
    obra_id: uuid.UUID,
    categoria: str | None,
    search: str | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    # Recurso aninhado: obra inexistente/de outro tenant (escondida pela RLS)
    # → 404, em vez de devolver página vazia silenciosa.
    if session.execute(text("SELECT 1 FROM obras WHERE id = :id"), {"id": obra_id}).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada")

    if cursor is not None:
        try:
            uuid.UUID(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cursor inválido"
            ) from exc

    # Busca vazia/em branco = sem filtro (evita plainto_tsquery('') que não casa
    # nada). plainto_tsquery tolera entrada livre do usuário (sem erro de sintaxe).
    if search is not None and not search.strip():
        search = None

    rows = (
        session.execute(
            text(
                f"SELECT {_OUT_COLUMNS} FROM documento "
                "WHERE obra_id = :obra_id AND deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:categoria AS text) IS NULL OR categoria = CAST(:categoria AS text)) "
                "  AND (CAST(:search AS text) IS NULL OR "
                "       to_tsvector('portuguese', "
                "         translate(nome, '._-/', '    ') || ' ' || coalesce(ocr_text, '')) "
                "       @@ plainto_tsquery('portuguese', translate(CAST(:search AS text), '._-/', '    '))) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {
                "obra_id": obra_id,
                "cursor": cursor,
                "categoria": categoria,
                "search": search,
                "limit_plus_one": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def update_documento(
    session: Session, *, documento_id: uuid.UUID, payload: DocumentoUpdate
) -> dict[str, Any]:
    existing = session.execute(
        text("SELECT 1 FROM documento WHERE id = :id AND deleted_at IS NULL FOR UPDATE"),
        {"id": documento_id},
    ).first()
    if existing is None:
        raise _NOT_FOUND

    data = payload.model_dump(exclude_unset=True)
    set_cols = [col for col in ("categoria", "visivel_cliente") if col in data]
    if not set_cols:
        return _get_out(session, documento_id)

    set_clause = ", ".join(f"{col} = :{col}" for col in set_cols)
    params: dict[str, Any] = {col: data[col] for col in set_cols}
    params["id"] = documento_id
    row = (
        session.execute(
            text(
                f"UPDATE documento SET {set_clause} "
                "WHERE id = :id AND deleted_at IS NULL "
                f"RETURNING {_OUT_COLUMNS}"
            ),
            params,
        )
        .mappings()
        .one()
    )
    return dict(row)


def soft_delete_documento(session: Session, documento_id: uuid.UUID) -> None:
    # Soft delete: mantém o objeto no storage (restauração/auditoria); a limpeza
    # física de órfãos fica para o job de cleanup.
    row = session.execute(
        text(
            "UPDATE documento SET deleted_at = now() "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": documento_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
