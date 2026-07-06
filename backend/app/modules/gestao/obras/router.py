"""Router `/api/v1/obras` — CRUD de obras (B2.3, US-02).

Leitura: qualquer usuário autenticado do tenant. Escrita (POST/PATCH/DELETE):
`owner`/`admin`/`gestor`. O isolamento por empresa é garantido pela RLS via
`get_db` (ver app/core/deps.py) — nenhum endpoint filtra `company_id` na mão.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.modules.gestao.obras import service
from app.modules.gestao.obras.schemas import (
    ObraCreate,
    ObraOut,
    ObraPage,
    ObraStatus,
    ObraUpdate,
)

router = APIRouter()

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "",
    response_model=ObraOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_obra(
    payload: ObraCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> ObraOut:
    row = service.create_obra(session, company_id=company_id, payload=payload)
    return ObraOut.model_validate(row)


@router.get("", response_model=ObraPage)
def list_obras(
    session: Session = Depends(get_db),
    status_filter: ObraStatus | None = Query(default=None, alias="status"),
    cliente_id: UUID | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> ObraPage:
    items, next_cursor = service.list_obras(
        session,
        status_filter=status_filter,
        cliente_id=cliente_id,
        cursor=cursor,
        limit=limit,
    )
    return ObraPage(items=[ObraOut.model_validate(row) for row in items], next_cursor=next_cursor)


@router.get("/{obra_id}", response_model=ObraOut)
def get_obra(obra_id: UUID, session: Session = Depends(get_db)) -> ObraOut:
    return ObraOut.model_validate(service.get_obra(session, obra_id))


@router.patch("/{obra_id}", response_model=ObraOut, dependencies=[Depends(_WRITE_ROLES)])
def update_obra(obra_id: UUID, payload: ObraUpdate, session: Session = Depends(get_db)) -> ObraOut:
    row = service.update_obra(session, obra_id=obra_id, payload=payload)
    return ObraOut.model_validate(row)


@router.delete(
    "/{obra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_obra(obra_id: UUID, session: Session = Depends(get_db)) -> None:
    service.soft_delete_obra(session, obra_id)
