"""Regras de negócio das ocorrências de campo (B8.4, US-18).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. `obra_id` é validada contra a RLS antes do INSERT (a FK
bypassa row-level security), como em documento/ticket.

Foto obrigatória: no create, as `photo_ids` informadas são vinculadas
(`photo.ocorrencia_id`) numa única UPDATE escopada pela obra + RLS. Se alguma
foto não existe, é de outra obra, já está vinculada ou é de outro tenant
(invisível pela RLS), a contagem não bate e a operação é revertida (422). As
`photo_ids` de saída vêm de um subselect agregado.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Session

from app.modules.gestao.ocorrencias.schemas import OcorrenciaCreate, OcorrenciaUpdate

# `photo_ids` agregado por subselect (evidências ligadas, ignorando removidas).
_OUT_COLUMNS = (
    "id, obra_id, titulo, descricao, status, gps_lat, gps_lng, created_at, "
    "COALESCE("
    "  (SELECT array_agg(p.id ORDER BY p.id) FROM photo p "
    "   WHERE p.ocorrencia_id = ocorrencia.id AND p.deleted_at IS NULL), "
    "  '{}'::uuid[]) AS photo_ids"
)
_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="ocorrência não encontrada"
)
_OBRA_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="obra não encontrada"
)
_FOTO_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="foto inválida: inexistente, de outra obra ou já vinculada",
)
_NADA_ATUALIZAR = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="nada para atualizar"
)

# Vínculo tipado do array de UUIDs: escopa pela obra + só fotos ainda livres.
# `RETURNING id` para contar as vinculadas (rowcount não é tipado no Result).
_LINK_FOTOS = text(
    "UPDATE photo SET ocorrencia_id = :ocorrencia_id "
    "WHERE id = ANY(:photo_ids) AND obra_id = :obra_id "
    "  AND ocorrencia_id IS NULL AND deleted_at IS NULL "
    "RETURNING id"
).bindparams(bindparam("photo_ids", type_=ARRAY(PgUUID(as_uuid=True))))


def _assert_obra_do_tenant(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _OBRA_INVALIDA


def _get_out(session: Session, ocorrencia_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_OUT_COLUMNS} FROM ocorrencia WHERE id = :id AND deleted_at IS NULL"),
            {"id": ocorrencia_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def create_ocorrencia(
    session: Session,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: OcorrenciaCreate,
) -> dict[str, Any]:
    _assert_obra_do_tenant(session, obra_id)

    ocorrencia_id = session.execute(
        text(
            "INSERT INTO ocorrencia "
            "(company_id, obra_id, titulo, descricao, gps_lat, gps_lng, created_by) "
            "VALUES (:company_id, :obra_id, :titulo, :descricao, :gps_lat, :gps_lng, :created_by) "
            "RETURNING id"
        ),
        {
            "company_id": company_id,
            "obra_id": obra_id,
            "titulo": payload.titulo,
            "descricao": payload.descricao,
            "gps_lat": payload.gps_lat,
            "gps_lng": payload.gps_lng,
            "created_by": created_by,
        },
    ).scalar_one()

    # Dedup preservando ordem: photo_ids repetidos não inflam a contagem esperada.
    unique_ids = list(dict.fromkeys(payload.photo_ids))
    linked = len(
        session.execute(
            _LINK_FOTOS,
            {"ocorrencia_id": ocorrencia_id, "photo_ids": unique_ids, "obra_id": obra_id},
        ).all()
    )
    if linked != len(unique_ids):
        # Alguma foto não pôde ser vinculada → estado inconsistente, reverte tudo.
        session.rollback()
        raise _FOTO_INVALIDA

    return _get_out(session, ocorrencia_id)


def list_ocorrencias(
    session: Session, *, obra_id: uuid.UUID, cursor: str | None, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
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
                f"SELECT {_OUT_COLUMNS} FROM ocorrencia "
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
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def get_ocorrencia(session: Session, ocorrencia_id: uuid.UUID) -> dict[str, Any]:
    return _get_out(session, ocorrencia_id)


def update_ocorrencia(
    session: Session, *, ocorrencia_id: uuid.UUID, payload: OcorrenciaUpdate
) -> dict[str, Any]:
    fields = payload.model_dump(exclude_unset=True)
    if "status" not in fields:
        raise _NADA_ATUALIZAR
    row = session.execute(
        text(
            "UPDATE ocorrencia SET status = CAST(:status AS ocorrencia_status) "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"status": fields["status"], "id": ocorrencia_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
    return _get_out(session, ocorrencia_id)
