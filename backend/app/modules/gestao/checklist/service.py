"""Regras de negócio do checklist de campo (B7.2, US-16).

Roda via `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. `obra_id` é validado contra a RLS de `obras` antes do
INSERT (a FK bypassa row-level security).

Ordenação: `sort_order` ASC, `id` ASC. `sort_order` é atribuído de forma
incremental na criação (fim da lista), então correlaciona com `id`. A paginação
usa keyset composto `(sort_order, id)` com cursor opaco (o `id` do último item),
correto mesmo se dois itens compartilham `sort_order`.

Toggle: quando `completed` vira `true`, o servidor carimba `completed_at` com
`now()`; ao voltar para `false`, zera. O relógio do cliente (offline) não é
fonte da verdade.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gestao.checklist.schemas import ChecklistItemCreate, ChecklistItemUpdate

_OUT_COLUMNS = "id, obra_id, titulo, completed, completed_at, sort_order, created_at"
_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="item de checklist não encontrado"
)
_OBRA_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada")
_NADA_ATUALIZAR = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="nada para atualizar"
)


def _assert_obra_existe(session: Session, obra_id: uuid.UUID) -> None:
    if session.execute(text("SELECT 1 FROM obras WHERE id = :id"), {"id": obra_id}).first() is None:
        raise _OBRA_NOT_FOUND


def create_item(
    session: Session, *, company_id: str, obra_id: uuid.UUID, payload: ChecklistItemCreate
) -> dict[str, Any]:
    _assert_obra_existe(session, obra_id)
    if payload.sort_order is not None:
        order = payload.sort_order
    else:
        order = session.execute(
            text(
                "SELECT coalesce(max(sort_order), -1) + 1 FROM checklist_item "
                "WHERE obra_id = :obra_id AND deleted_at IS NULL"
            ),
            {"obra_id": obra_id},
        ).scalar_one()
    row = (
        session.execute(
            text(
                "INSERT INTO checklist_item (company_id, obra_id, titulo, sort_order) "
                "VALUES (:company_id, :obra_id, :titulo, :sort_order) "
                f"RETURNING {_OUT_COLUMNS}"
            ),
            {
                "company_id": company_id,
                "obra_id": obra_id,
                "titulo": payload.titulo,
                "sort_order": order,
            },
        )
        .mappings()
        .first()
    )
    assert row is not None  # INSERT ... RETURNING sempre devolve a linha
    return dict(row)


def list_items(
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
                f"SELECT {_OUT_COLUMNS} FROM checklist_item "
                "WHERE obra_id = :obra_id AND deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR "
                "       (sort_order, id) > ("
                "         (SELECT sort_order FROM checklist_item WHERE id = CAST(:cursor AS uuid)), "
                "         CAST(:cursor AS uuid))) "
                "ORDER BY sort_order, id "
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


def update_item(
    session: Session, *, item_id: uuid.UUID, payload: ChecklistItemUpdate
) -> dict[str, Any]:
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise _NADA_ATUALIZAR

    sets: list[str] = []
    params: dict[str, Any] = {"id": item_id}
    if "titulo" in fields:
        sets.append("titulo = :titulo")
        params["titulo"] = fields["titulo"]
    if "sort_order" in fields:
        sets.append("sort_order = :sort_order")
        params["sort_order"] = fields["sort_order"]
    if "completed" in fields:
        # completed_at é carimbado pelo servidor no toggle (o relógio offline do
        # cliente não é fonte da verdade).
        sets.append("completed = :completed")
        sets.append("completed_at = CASE WHEN :completed THEN now() ELSE NULL END")
        params["completed"] = fields["completed"]

    row = (
        session.execute(
            text(
                f"UPDATE checklist_item SET {', '.join(sets)} "
                f"WHERE id = :id AND deleted_at IS NULL RETURNING {_OUT_COLUMNS}"
            ),
            params,
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def delete_item(session: Session, *, item_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE checklist_item SET deleted_at = now() "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": item_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
