"""Regras de negócio do CRUD de clientes (B2.2).

Roda sempre via `get_db` (role `app_user`, RLS ativa com `app.company_id`
setado) — nenhuma query filtra `company_id` manualmente: a RLS garante o
isolamento. O `INSERT` inclui `company_id` explícito (NOT NULL + exigido pelo
`WITH CHECK` da policy).

SQL cru via `text()` para manter o estilo dos demais módulos (auth/users).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.gestao.clientes.schemas import ClienteCreate, ClienteUpdate
from app.modules.gestao.clientes.validators import validate_documento

_COLUMNS = "id, tipo_pessoa, documento, nome, telefone, email, created_at"
_DUP = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="documento já cadastrado para esta empresa"
)
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cliente não encontrado")


def create_cliente(session: Session, *, company_id: str, payload: ClienteCreate) -> dict[str, Any]:
    try:
        row = (
            session.execute(
                text(
                    "INSERT INTO clientes "
                    "(company_id, tipo_pessoa, documento, nome, telefone, email) "
                    "VALUES (:company_id, :tipo_pessoa, :documento, :nome, :telefone, :email) "
                    f"RETURNING {_COLUMNS}"
                ),
                {
                    "company_id": company_id,
                    "tipo_pessoa": payload.tipo_pessoa,
                    "documento": payload.documento,
                    "nome": payload.nome,
                    "telefone": payload.telefone,
                    "email": payload.email,
                },
            )
            .mappings()
            .one()
        )
    except IntegrityError as exc:
        raise _DUP from exc
    return dict(row)


def list_clientes(
    session: Session,
    *,
    search: str | None,
    tipo: str | None,
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

    like = f"%{search}%" if search else None
    rows = (
        session.execute(
            text(
                # CASTs explícitos: parâmetros usados só em `:x IS NULL` não têm
                # tipo inferível pelo Postgres (AmbiguousParameter) — o cast fixa
                # o tipo em ambas as ocorrências de cada bind.
                f"SELECT {_COLUMNS} FROM clientes "
                "WHERE deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:tipo AS text) IS NULL OR tipo_pessoa = CAST(:tipo AS text)) "
                "  AND (CAST(:like AS text) IS NULL "
                "       OR nome ILIKE CAST(:like AS text) "
                "       OR documento ILIKE CAST(:like AS text)) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {"cursor": cursor, "tipo": tipo, "like": like, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def get_cliente(session: Session, cliente_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_COLUMNS} FROM clientes WHERE id = :id AND deleted_at IS NULL"),
            {"id": cliente_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def update_cliente(
    session: Session, *, cliente_id: uuid.UUID, payload: ClienteUpdate
) -> dict[str, Any]:
    existing = (
        session.execute(
            text(
                "SELECT tipo_pessoa, documento FROM clientes "
                "WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": cliente_id},
        )
        .mappings()
        .first()
    )
    if existing is None:
        raise _NOT_FOUND

    data = payload.model_dump(exclude_unset=True)
    if "documento" in data or "tipo_pessoa" in data:
        eff_tipo = data.get("tipo_pessoa", existing["tipo_pessoa"])
        eff_doc = data.get("documento", existing["documento"])
        try:
            data["documento"] = validate_documento(eff_tipo, eff_doc)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    columns = ("tipo_pessoa", "documento", "nome", "telefone", "email")
    set_cols = [col for col in columns if col in data]
    if not set_cols:
        return get_cliente(session, cliente_id)

    set_clause = ", ".join(f"{col} = :{col}" for col in set_cols)
    params: dict[str, Any] = {col: data[col] for col in set_cols}
    params["id"] = cliente_id
    try:
        row = (
            session.execute(
                text(
                    f"UPDATE clientes SET {set_clause} "
                    "WHERE id = :id AND deleted_at IS NULL "
                    f"RETURNING {_COLUMNS}"
                ),
                params,
            )
            .mappings()
            .one()
        )
    except IntegrityError as exc:
        raise _DUP from exc
    return dict(row)


def soft_delete_cliente(session: Session, cliente_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE clientes SET deleted_at = now() "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": cliente_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
