"""Router `/api/v1/clientes` — CRUD de clientes (B2.2, US-01 prep).

Leitura: qualquer usuário autenticado do tenant. Escrita (POST/PATCH/DELETE):
`owner`/`admin`/`gestor`. O isolamento por empresa é garantido pela RLS via
`get_db` (ver app/core/deps.py) — nenhum endpoint filtra `company_id` na mão.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.modules.gestao.clientes import service
from app.modules.gestao.clientes.schemas import (
    ClienteCreate,
    ClienteOut,
    ClientePage,
    ClienteUpdate,
    TipoPessoa,
)

router = APIRouter()

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "",
    response_model=ClienteOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_cliente(
    payload: ClienteCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> ClienteOut:
    row = service.create_cliente(session, company_id=company_id, payload=payload)
    return ClienteOut.model_validate(row)


@router.get("", response_model=ClientePage)
def list_clientes(
    session: Session = Depends(get_db),
    search: str | None = Query(default=None),
    tipo: TipoPessoa | None = Query(default=None, alias="type"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> ClientePage:
    items, next_cursor = service.list_clientes(
        session, search=search, tipo=tipo, cursor=cursor, limit=limit
    )
    return ClientePage(
        items=[ClienteOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.get("/{cliente_id}", response_model=ClienteOut)
def get_cliente(cliente_id: UUID, session: Session = Depends(get_db)) -> ClienteOut:
    return ClienteOut.model_validate(service.get_cliente(session, cliente_id))


@router.patch("/{cliente_id}", response_model=ClienteOut, dependencies=[Depends(_WRITE_ROLES)])
def update_cliente(
    cliente_id: UUID, payload: ClienteUpdate, session: Session = Depends(get_db)
) -> ClienteOut:
    row = service.update_cliente(session, cliente_id=cliente_id, payload=payload)
    return ClienteOut.model_validate(row)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_cliente(cliente_id: UUID, session: Session = Depends(get_db)) -> None:
    service.soft_delete_cliente(session, cliente_id)
