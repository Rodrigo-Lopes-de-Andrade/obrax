"""Regras de negócio do sync de fotos de campo (B8.2 sync, B8.3 confirm; US-09/US-17).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. `obra_id` é validada contra a RLS antes do INSERT (a FK
bypassa row-level security), como em documento/ticket.

Fluxo (igual a documento, com idempotência por `client_photo_id`):
- `sync_photo`: cria a linha `pendente` e devolve a URL de `PUT` assinada. É
  idempotente pela chave do aparelho — reenviar o mesmo `client_photo_id`
  devolve a mesma linha (retry após queda de rede). Se essa foto já está
  `sincronizado`, ou se o mesmo conteúdo (sha256) já foi enviado sob outra
  chave, responde 409 (o cliente tira da fila).
- `confirm_photo`: valida tamanho (HEAD) e SHA-256 (baixa o objeto), marca
  `sincronizado` e carimba `synced_at`. Idempotente: reconfirmar devolve o
  estado atual.

`storage_path` guarda só a chave no bucket (nunca a URL); a `download_url` é
assinada sob demanda a cada leitura (docs/CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.storage import StorageClient
from app.modules.gestao.fotos.schemas import MAX_PHOTO_BYTES, PhotoSyncCreate

# TTL da URL de download da foto na galeria — curto, re-assinada a cada leitura.
_DOWNLOAD_TTL_SECONDS = 900

_RAW_COLUMNS = (
    "id, obra_id, ocorrencia_id, client_photo_id, sha256, size_bytes, "
    "sync_status, captured_at, synced_at, created_at, storage_path"
)
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="foto não encontrada")
_OBRA_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="obra não encontrada"
)
_JA_SINCRONIZADA = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="foto já sincronizada"
)
_CONTEUDO_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="foto duplicada: mesmo conteúdo (sha256) já enviado nesta empresa",
)


def _storage_key(company_id: str, obra_id: uuid.UUID, photo_id: uuid.UUID) -> str:
    return f"{company_id}/{obra_id}/{photo_id}"


def _to_out(storage: StorageClient, row: dict[str, Any]) -> dict[str, Any]:
    """Converte a linha crua em PhotoOut: troca `storage_path` por uma
    `download_url` assinada (ou `None` se ainda pendente)."""
    out = dict(row)
    key = out.pop("storage_path")
    out["download_url"] = (
        storage.presigned_get_url(key=key, expires_in=_DOWNLOAD_TTL_SECONDS) if key else None
    )
    return out


def _assert_obra_do_tenant(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _OBRA_INVALIDA


def _presigned_for(
    storage: StorageClient, *, company_id: str, obra_id: uuid.UUID, photo_id: uuid.UUID
) -> dict[str, Any]:
    presigned = storage.presigned_put_url(key=_storage_key(company_id, obra_id, photo_id))
    return {
        "photo_id": photo_id,
        "upload_url": presigned.url,
        "method": presigned.method,
        "expires_in": presigned.expires_in,
    }


def sync_photo(
    session: Session,
    storage: StorageClient,
    *,
    company_id: str,
    client_photo_id: uuid.UUID,
    payload: PhotoSyncCreate,
) -> dict[str, Any]:
    _assert_obra_do_tenant(session, payload.obra_id)

    # Idempotência pela chave do aparelho: mesma foto reenviada cai na linha
    # existente (retry após timeout). Já sincronizada → 409 (tira da fila).
    existing = (
        session.execute(
            text(
                "SELECT id, obra_id, sync_status FROM photo "
                "WHERE client_photo_id = :cpid AND deleted_at IS NULL"
            ),
            {"cpid": client_photo_id},
        )
        .mappings()
        .first()
    )
    if existing is not None:
        if existing["sync_status"] == "sincronizado":
            raise _JA_SINCRONIZADA
        return _presigned_for(
            storage, company_id=company_id, obra_id=existing["obra_id"], photo_id=existing["id"]
        )

    # Dedup por conteúdo: mesmo arquivo (sha256) já enviado sob outra chave.
    dup = session.execute(
        text("SELECT 1 FROM photo WHERE sha256 = :sha256 AND deleted_at IS NULL"),
        {"sha256": payload.sha256},
    ).first()
    if dup is not None:
        raise _CONTEUDO_DUPLICADO

    try:
        photo_id = session.execute(
            text(
                "INSERT INTO photo "
                "(company_id, obra_id, client_photo_id, sha256, size_bytes, captured_at) "
                "VALUES (:company_id, :obra_id, :client_photo_id, :sha256, :size_bytes, "
                " :captured_at) "
                "RETURNING id"
            ),
            {
                "company_id": company_id,
                "obra_id": payload.obra_id,
                "client_photo_id": client_photo_id,
                "sha256": payload.sha256,
                "size_bytes": payload.size_bytes,
                "captured_at": payload.captured_at,
            },
        ).scalar_one()
    except IntegrityError as exc:
        # Corrida no mesmo client_photo_id (dois sync simultâneos): a UNIQUE
        # parcial é o backstop — devolve a linha já criada.
        session.rollback()
        row = (
            session.execute(
                text(
                    "SELECT id, obra_id, sync_status FROM photo "
                    "WHERE client_photo_id = :cpid AND deleted_at IS NULL"
                ),
                {"cpid": client_photo_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise
        if row["sync_status"] == "sincronizado":
            raise _JA_SINCRONIZADA from exc
        return _presigned_for(
            storage, company_id=company_id, obra_id=row["obra_id"], photo_id=row["id"]
        )

    return _presigned_for(
        storage, company_id=company_id, obra_id=payload.obra_id, photo_id=photo_id
    )


def confirm_photo(
    session: Session,
    storage: StorageClient,
    *,
    photo_id: uuid.UUID,
) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                "SELECT company_id, obra_id, size_bytes, sha256, sync_status, storage_path "
                "FROM photo WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": photo_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND

    # Idempotente: reconfirmar uma foto já sincronizada devolve o estado atual
    # (o cliente pode reenviar o confirm após um timeout de rede).
    if row["sync_status"] == "sincronizado":
        return get_photo(session, storage, photo_id)

    key = _storage_key(str(row["company_id"]), row["obra_id"], photo_id)
    stat = storage.stat(key=key)
    if stat is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="arquivo não encontrado no storage — upload não concluído",
        )
    if stat.size_bytes > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="foto excede o limite de 2 MB",
        )
    if stat.size_bytes != row["size_bytes"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tamanho do arquivo diverge do informado no sync",
        )

    # Integridade: o cliente sobe direto no bucket, então conferimos o SHA-256
    # do conteúdo contra o hash informado (a foto é pequena, <=2 MB).
    if hashlib.sha256(storage.get_object(key=key)).hexdigest() != row["sha256"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sha256 do arquivo diverge do informado no sync",
        )

    updated = (
        session.execute(
            text(
                "UPDATE photo SET sync_status = 'sincronizado', storage_path = :key, "
                "synced_at = now() WHERE id = :id AND deleted_at IS NULL "
                f"RETURNING {_RAW_COLUMNS}"
            ),
            {"key": key, "id": photo_id},
        )
        .mappings()
        .one()
    )
    return _to_out(storage, dict(updated))


def get_photo(session: Session, storage: StorageClient, photo_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_RAW_COLUMNS} FROM photo WHERE id = :id AND deleted_at IS NULL"),
            {"id": photo_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return _to_out(storage, dict(row))


def list_photos(
    session: Session,
    storage: StorageClient,
    *,
    obra_id: uuid.UUID,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    # Recurso aninhado: obra inexistente/de outro tenant (escondida pela RLS) →
    # 404, em vez de página vazia silenciosa.
    if session.execute(text("SELECT 1 FROM obras WHERE id = :id"), {"id": obra_id}).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada")

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
                f"SELECT {_RAW_COLUMNS} FROM photo "
                "WHERE obra_id = :obra_id AND deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {"obra_id": obra_id, "cursor": cursor, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [_to_out(storage, dict(r)) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor
