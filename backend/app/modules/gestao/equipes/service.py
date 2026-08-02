"""Regras de negócio do CRUD de equipe (B3.6).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. `obra_id` e `user_id` são validados contra a RLS antes do
INSERT (FK bypassa row-level security): a obra pela policy de `obras` e o usuário
por existir em `user_company_role` do tenant atual — senão dá para vincular
obra/usuário de outro tenant.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.gestao.equipes.schemas import MembroCreate

_OUT_COLUMNS = "m.id, m.user_id, u.nome, u.email, m.papel, m.created_at"
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membro não encontrado")
_OBRA_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada")
_USER_INVALIDO = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="usuário não encontrado"
)
_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="usuário já é membro ativo desta obra"
)


def _assert_obra_existe(session: Session, obra_id: uuid.UUID) -> None:
    if session.execute(text("SELECT 1 FROM obras WHERE id = :id"), {"id": obra_id}).first() is None:
        raise _OBRA_NOT_FOUND


def _get_membro_out(session: Session, membro_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                f"SELECT {_OUT_COLUMNS} FROM obra_membro m JOIN users u ON u.id = m.user_id "
                "WHERE m.id = :id AND m.deleted_at IS NULL"
            ),
            {"id": membro_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def add_membro(
    session: Session, *, company_id: str, obra_id: uuid.UUID, payload: MembroCreate
) -> dict[str, Any]:
    _assert_obra_existe(session, obra_id)
    # Usuário precisa pertencer ao tenant (RLS de user_company_role já restringe
    # ao company_id do contexto).
    if (
        session.execute(
            text("SELECT 1 FROM user_company_role WHERE user_id = :uid"),
            {"uid": payload.user_id},
        ).first()
        is None
    ):
        raise _USER_INVALIDO

    try:
        membro_id = session.execute(
            text(
                "INSERT INTO obra_membro (company_id, obra_id, user_id, papel) "
                "VALUES (:company_id, :obra_id, :user_id, :papel) RETURNING id"
            ),
            {
                "company_id": company_id,
                "obra_id": obra_id,
                "user_id": payload.user_id,
                "papel": payload.papel,
            },
        ).scalar_one()
    except IntegrityError as exc:
        session.rollback()
        raise _DUPLICADO from exc

    return _get_membro_out(session, membro_id)


def list_membros(
    session: Session, *, obra_id: uuid.UUID, cursor: str | None, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    _assert_obra_existe(session, obra_id)

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
                f"SELECT {_OUT_COLUMNS} FROM obra_membro m JOIN users u ON u.id = m.user_id "
                "WHERE m.obra_id = :obra_id AND m.deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR m.id < CAST(:cursor AS uuid)) "
                "ORDER BY m.id DESC "
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


def search_usuarios(
    session: Session, *, search: str, limit: int
) -> tuple[list[dict[str, Any]], str | None]:
    """Usuários do tenant para o seletor de membros/menções (US-07). A RLS de
    `user_company_role` já restringe ao company atual — o join só devolve quem
    pertence a esta empresa. Busca opcional por nome/email (ILIKE)."""
    termo = search.strip()
    pattern = f"%{termo}%"
    rows = (
        session.execute(
            text(
                "SELECT u.id, u.nome, u.email, ucr.role "
                "FROM users u JOIN user_company_role ucr ON ucr.user_id = u.id "
                "WHERE u.deleted_at IS NULL "
                "  AND (:termo = '' OR u.nome ILIKE :pattern OR u.email ILIKE :pattern) "
                "ORDER BY u.nome ASC, u.id ASC "
                "LIMIT :limit_plus_one"
            ),
            {"termo": termo, "pattern": pattern, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def remove_membro(session: Session, *, obra_id: uuid.UUID, user_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE obra_membro SET deleted_at = now() "
            "WHERE obra_id = :obra_id AND user_id = :user_id AND deleted_at IS NULL RETURNING id"
        ),
        {"obra_id": obra_id, "user_id": user_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
