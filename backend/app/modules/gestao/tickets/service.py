"""Regras de negócio do CRUD de tickets (B4.2).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. `obra_id` é validada contra a RLS antes do INSERT (FK
bypassa row-level security), como em documentos/equipes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from app.modules.gestao.tickets.schemas import MensagemCreate, TicketCreate

_COLUMNS = "id, obra_id, titulo, descricao, status, created_by, created_at"
_MSG_COLUMNS = "id, ticket_id, author_id, content, attachment_paths, created_at"
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ticket não encontrado")
_OBRA_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="obra não encontrada"
)


def _assert_obra_do_tenant(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _OBRA_INVALIDA


def create_ticket(
    session: Session,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: TicketCreate,
) -> dict[str, Any]:
    _assert_obra_do_tenant(session, obra_id)
    row = (
        session.execute(
            text(
                "INSERT INTO ticket (company_id, obra_id, titulo, descricao, created_by) "
                "VALUES (:company_id, :obra_id, :titulo, :descricao, :created_by) "
                f"RETURNING {_COLUMNS}"
            ),
            {
                "company_id": company_id,
                "obra_id": obra_id,
                "titulo": payload.titulo,
                "descricao": payload.descricao,
                "created_by": created_by,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def list_tickets(
    session: Session,
    *,
    obra_id: uuid.UUID | None,
    status_filter: str | None,
    cursor: str | None,
    limit: int,
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
                f"SELECT {_COLUMNS} FROM ticket "
                "WHERE deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:obra_id AS uuid) IS NULL OR obra_id = CAST(:obra_id AS uuid)) "
                "  AND (CAST(:status AS ticket_status) IS NULL "
                "       OR status = CAST(:status AS ticket_status)) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {
                "cursor": cursor,
                "obra_id": obra_id,
                "status": status_filter,
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


def get_ticket(session: Session, ticket_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_COLUMNS} FROM ticket WHERE id = :id AND deleted_at IS NULL"),
            {"id": ticket_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def update_status(session: Session, *, ticket_id: uuid.UUID, new_status: str) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                "UPDATE ticket SET status = CAST(:status AS ticket_status) "
                "WHERE id = :id AND deleted_at IS NULL "
                f"RETURNING {_COLUMNS}"
            ),
            {"status": new_status, "id": ticket_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def soft_delete_ticket(session: Session, ticket_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE ticket SET deleted_at = now() "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": ticket_id},
    ).first()
    if row is None:
        raise _NOT_FOUND


def list_notify_emails(session: Session) -> list[str]:
    """E-mails dos owners/admins do tenant, para avisar de um novo chamado
    (B4.5). Escopado por RLS: `user_company_role` filtra pelo tenant e a policy
    de SELECT de `users` só expõe usuários vinculados a ele."""
    rows = session.execute(
        text(
            "SELECT u.email FROM users u "
            "JOIN user_company_role ucr ON ucr.user_id = u.id "
            "WHERE u.deleted_at IS NULL AND ucr.role IN ('owner', 'admin') "
            "ORDER BY u.email"
        )
    ).scalars()
    return list(rows)


def _assert_ticket_do_tenant(session: Session, ticket_id: uuid.UUID) -> None:
    """Ticket inexistente/de outro tenant (escondido pela RLS) → 404, em vez de
    inserir/listar mensagem num ticket que o tenant não enxerga."""
    row = session.execute(
        text("SELECT 1 FROM ticket WHERE id = :id AND deleted_at IS NULL"),
        {"id": ticket_id},
    ).first()
    if row is None:
        raise _NOT_FOUND


# Bind tipado do array: SQLAlchemy serializa `list[str]` como `text[]` de forma
# robusta (inclusive lista vazia → '{}'), sem CAST manual no SQL.
_INSERT_MENSAGEM = text(
    "INSERT INTO ticket_mensagem "
    "(company_id, ticket_id, author_id, content, attachment_paths) "
    "VALUES (:company_id, :ticket_id, :author_id, :content, :attachment_paths) "
    f"RETURNING {_MSG_COLUMNS}"
).bindparams(bindparam("attachment_paths", type_=ARRAY(Text)))


def create_mensagem(
    session: Session,
    *,
    company_id: str,
    ticket_id: uuid.UUID,
    author_id: uuid.UUID,
    payload: MensagemCreate,
) -> dict[str, Any]:
    _assert_ticket_do_tenant(session, ticket_id)
    row = (
        session.execute(
            _INSERT_MENSAGEM,
            {
                "company_id": company_id,
                "ticket_id": ticket_id,
                "author_id": author_id,
                "content": payload.content,
                "attachment_paths": payload.attachment_paths,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def list_mensagens(
    session: Session,
    *,
    ticket_id: uuid.UUID,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    _assert_ticket_do_tenant(session, ticket_id)
    if cursor is not None:
        try:
            uuid.UUID(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cursor inválido"
            ) from exc

    # Mais recentes primeiro (id v7 ~ tempo), como as demais listagens; o chat
    # carrega histórico mais antigo via `next_cursor` e inverte na exibição.
    rows = (
        session.execute(
            text(
                f"SELECT {_MSG_COLUMNS} FROM ticket_mensagem "
                "WHERE ticket_id = :ticket_id "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {"ticket_id": ticket_id, "cursor": cursor, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor
