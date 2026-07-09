"""Router de tickets — chamados de obra (B4.2, US-08).

Montado sem prefixo (paths absolutos): create aninhado na obra
(`/obras/{id}/tickets`) e os demais planos (`/tickets*`), conforme
docs/ESPEC.md § 6. Abrir chamado: qualquer usuário do tenant. Mudar status /
excluir: `owner`/`admin`/`gestor`. Isolamento por empresa via RLS no `get_db`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.modules.gestao.tickets import service
from app.modules.gestao.tickets.schemas import (
    TicketCreate,
    TicketOut,
    TicketPage,
    TicketStatus,
    TicketStatusUpdate,
)

router = APIRouter(tags=["tickets"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "/obras/{obra_id}/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    obra_id: UUID,
    payload: TicketCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> TicketOut:
    row = service.create_ticket(
        session,
        company_id=company_id,
        obra_id=obra_id,
        created_by=auth.user_id,
        payload=payload,
    )
    return TicketOut.model_validate(row)


@router.get("/tickets", response_model=TicketPage)
def list_tickets(
    session: Session = Depends(get_db),
    obra_id: UUID | None = Query(default=None),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> TicketPage:
    items, next_cursor = service.list_tickets(
        session,
        obra_id=obra_id,
        status_filter=status_filter,
        cursor=cursor,
        limit=limit,
    )
    return TicketPage(
        items=[TicketOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: UUID, session: Session = Depends(get_db)) -> TicketOut:
    return TicketOut.model_validate(service.get_ticket(session, ticket_id))


@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_status(
    ticket_id: UUID,
    payload: TicketStatusUpdate,
    session: Session = Depends(get_db),
) -> TicketOut:
    row = service.update_status(session, ticket_id=ticket_id, new_status=payload.status)
    return TicketOut.model_validate(row)


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_ticket(ticket_id: UUID, session: Session = Depends(get_db)) -> None:
    service.soft_delete_ticket(session, ticket_id)
