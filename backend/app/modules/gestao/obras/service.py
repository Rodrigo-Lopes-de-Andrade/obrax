"""Regras de negócio do CRUD de obras (B2.3).

Roda sempre via `get_db` (role `app_user`, RLS ativa com `app.company_id`
setado) — nenhuma query filtra `company_id` na mão. O INSERT inclui
`company_id` explícito (NOT NULL + exigido pelo WITH CHECK da policy).

`cliente_id` é validado contra a RLS antes do INSERT: a checagem de FK do
Postgres bypassa row-level security (integridade referencial roda fora da
policy), então sem esse SELECT prévio seria possível criar uma obra apontando
para um cliente de outro tenant. O SELECT sob `app_user` só enxerga clientes do
tenant atual — não achou, 422.

CASTs explícitos em `:status` (enum `obra_status`) e nos binds usados em
`:x IS NULL` da listagem: parâmetros sem contexto de tipo geram
`AmbiguousParameter` no Postgres.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gestao.obras.schemas import ObraCreate, ObraUpdate
from app.modules.gestao.obras.validators import validate_date_order

_COLUMNS = (
    "id, cliente_id, status, codigo, nome, data_inicio, "
    "data_prevista_fim, data_real_fim, valor_contrato, created_at"
)
_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada")
_CLIENTE_INVALIDO = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cliente não encontrado"
)


def _assert_cliente_do_tenant(session: Session, cliente_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM clientes WHERE id = :id AND deleted_at IS NULL"),
        {"id": cliente_id},
    ).first()
    if row is None:
        raise _CLIENTE_INVALIDO


def create_obra(session: Session, *, company_id: str, payload: ObraCreate) -> dict[str, Any]:
    _assert_cliente_do_tenant(session, payload.cliente_id)
    row = (
        session.execute(
            text(
                "INSERT INTO obras "
                "(company_id, cliente_id, status, codigo, nome, data_inicio, "
                " data_prevista_fim, data_real_fim, valor_contrato) "
                "VALUES (:company_id, :cliente_id, CAST(:status AS obra_status), :codigo, "
                " :nome, :data_inicio, :data_prevista_fim, :data_real_fim, :valor_contrato) "
                f"RETURNING {_COLUMNS}"
            ),
            {
                "company_id": company_id,
                "cliente_id": payload.cliente_id,
                "status": payload.status,
                "codigo": payload.codigo,
                "nome": payload.nome,
                "data_inicio": payload.data_inicio,
                "data_prevista_fim": payload.data_prevista_fim,
                "data_real_fim": payload.data_real_fim,
                "valor_contrato": payload.valor_contrato,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def list_obras(
    session: Session,
    *,
    status_filter: str | None,
    cliente_id: uuid.UUID | None,
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
                f"SELECT {_COLUMNS} FROM obras "
                "WHERE deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:status AS obra_status) IS NULL "
                "       OR status = CAST(:status AS obra_status)) "
                "  AND (CAST(:cliente_id AS uuid) IS NULL "
                "       OR cliente_id = CAST(:cliente_id AS uuid)) "
                "ORDER BY id DESC "
                "LIMIT :limit_plus_one"
            ),
            {
                "cursor": cursor,
                "status": status_filter,
                "cliente_id": cliente_id,
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


def get_obra(session: Session, obra_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(f"SELECT {_COLUMNS} FROM obras WHERE id = :id AND deleted_at IS NULL"),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return dict(row)


def update_obra(session: Session, *, obra_id: uuid.UUID, payload: ObraUpdate) -> dict[str, Any]:
    existing = (
        session.execute(
            text(
                "SELECT data_inicio, data_prevista_fim FROM obras "
                "WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if existing is None:
        raise _NOT_FOUND

    data = payload.model_dump(exclude_unset=True)
    if "data_inicio" in data or "data_prevista_fim" in data:
        eff_inicio = data.get("data_inicio", existing["data_inicio"])
        eff_fim = data.get("data_prevista_fim", existing["data_prevista_fim"])
        try:
            validate_date_order(eff_inicio, eff_fim)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    columns = (
        "status",
        "codigo",
        "nome",
        "data_inicio",
        "data_prevista_fim",
        "data_real_fim",
        "valor_contrato",
    )
    set_cols = [col for col in columns if col in data]
    if not set_cols:
        return get_obra(session, obra_id)

    set_clause = ", ".join(
        f"{col} = CAST(:{col} AS obra_status)" if col == "status" else f"{col} = :{col}"
        for col in set_cols
    )
    params: dict[str, Any] = {col: data[col] for col in set_cols}
    params["id"] = obra_id
    row = (
        session.execute(
            text(
                f"UPDATE obras SET {set_clause} "
                "WHERE id = :id AND deleted_at IS NULL "
                f"RETURNING {_COLUMNS}"
            ),
            params,
        )
        .mappings()
        .one()
    )
    return dict(row)


def soft_delete_obra(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE obras SET deleted_at = now() WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
