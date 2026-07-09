"""Router de tickets — chamados de obra (B4.2 CRUD, B4.3 chat, B4.5 e-mail; US-08).

Montado sem prefixo (paths absolutos): create aninhado na obra
(`/obras/{id}/tickets`) e os demais planos (`/tickets*`), conforme
docs/ESPEC.md § 6. Abrir chamado e conversar no chat: qualquer usuário do
tenant (o cliente também responde). Mudar status / excluir:
`owner`/`admin`/`gestor`. Isolamento por empresa via RLS no `get_db`.

Realtime (B4.3): ao gravar uma mensagem, transmitimos um evento no canal do
ticket via `events.emit`. Notificação (B4.5): ao abrir um chamado, avisamos os
owners/admins por e-mail via `notifications.notify_safe`. Ambos best-effort e
desacoplados do INSERT — no-op em dev/CI, plugáveis em staging/prod (ver
app/integrations/events.py e app/integrations/notifications.py).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.integrations.events import DomainEvent, EventPublisher, emit, get_event_publisher
from app.integrations.notifications import EmailMessage, Notifier, get_notifier, notify_safe
from app.modules.gestao.tickets import service
from app.modules.gestao.tickets.schemas import (
    MensagemCreate,
    MensagemOut,
    MensagemPage,
    TicketCreate,
    TicketOut,
    TicketPage,
    TicketStatus,
    TicketStatusUpdate,
)

router = APIRouter(tags=["tickets"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor")

# Nome do evento de realtime (mesmo string que o frontend escuta no canal).
EVENT_MENSAGEM_CREATED = "ticket.mensagem.created"


def _notify_ticket_criado(session: Session, notifier: Notifier, ticket: TicketOut) -> None:
    """Avisa owners/admins do tenant que um chamado foi aberto (B4.5). Resolve
    os destinatários sob a mesma sessão RLS; sem destinatários, não faz nada."""
    emails = service.list_notify_emails(session)
    message = EmailMessage(
        to=tuple(emails),
        subject=f"Novo chamado: {ticket.titulo}",
        body=(
            "Um novo chamado foi aberto.\n\n"
            f"Título: {ticket.titulo}\n"
            f"Descrição: {ticket.descricao or '—'}\n"
            f"Obra: {ticket.obra_id}\n"
        ),
        template="ticket_created",
        context={
            "ticket_id": str(ticket.id),
            "obra_id": str(ticket.obra_id),
            "titulo": ticket.titulo,
            "descricao": ticket.descricao,
        },
    )
    notify_safe(notifier, message)


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
    notifier: Notifier = Depends(get_notifier),
) -> TicketOut:
    row = service.create_ticket(
        session,
        company_id=company_id,
        obra_id=obra_id,
        created_by=auth.user_id,
        payload=payload,
    )
    out = TicketOut.model_validate(row)
    _notify_ticket_criado(session, notifier, out)
    return out


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


@router.post(
    "/tickets/{ticket_id}/mensagens",
    response_model=MensagemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_mensagem(
    ticket_id: UUID,
    payload: MensagemCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> MensagemOut:
    row = service.create_mensagem(
        session,
        company_id=company_id,
        ticket_id=ticket_id,
        author_id=auth.user_id,
        payload=payload,
    )
    out = MensagemOut.model_validate(row)
    # Persistiu → transmite no canal do ticket. `emit` é best-effort: uma falha
    # de realtime nunca derruba o request (o banco é a fonte da verdade).
    emit(
        publisher,
        DomainEvent(
            channel=f"ticket:{ticket_id}",
            event=EVENT_MENSAGEM_CREATED,
            payload=out.model_dump(mode="json"),
        ),
    )
    return out


@router.get("/tickets/{ticket_id}/mensagens", response_model=MensagemPage)
def list_mensagens(
    ticket_id: UUID,
    session: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> MensagemPage:
    items, next_cursor = service.list_mensagens(
        session, ticket_id=ticket_id, cursor=cursor, limit=limit
    )
    return MensagemPage(
        items=[MensagemOut.model_validate(row) for row in items], next_cursor=next_cursor
    )
