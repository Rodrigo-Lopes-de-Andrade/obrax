"""Router de fotos de campo (B8.2 sync, B8.3 confirm; US-09/US-17).

Montado sem prefixo (paths absolutos), conforme o contrato (docs/CLAUDE.md):
`POST /photos/sync` (idempotente por `Idempotency-Key`) e
`POST /photos/{id}/confirm`; a galeria fica aninhada na obra
(`GET /obras/{id}/photos`). Isolamento por empresa via RLS no `get_db`.

Escrita (sync/confirm): owner/admin/gestor/**campo** — capturar foto é ação de
campo. Leitura (galeria): qualquer usuário do tenant.

Realtime (B8.3/F8.6): ao confirmar, transmitimos um evento no canal da obra
(`obra:{id}:fotos`) via `events.emit` — best-effort, no-op em dev/CI, plugável
em staging/prod (ver app/integrations/events.py). Uma falha de entrega nunca
derruba o confirm (o banco é a fonte da verdade).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.integrations.events import DomainEvent, EventPublisher, emit, get_event_publisher
from app.integrations.storage import StorageClient, get_storage_client
from app.modules.gestao.fotos import service
from app.modules.gestao.fotos.schemas import (
    PhotoOut,
    PhotoPage,
    PhotoSyncCreate,
    PhotoSyncOut,
)

router = APIRouter(tags=["fotos"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor", "campo")

# Nome do evento de realtime (mesmo string que o frontend escuta no canal).
EVENT_FOTO_SINCRONIZADA = "foto.sincronizada"


@router.post(
    "/photos/sync",
    response_model=PhotoSyncOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def sync_photo(
    payload: PhotoSyncCreate,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> PhotoSyncOut:
    result = service.sync_photo(
        session,
        storage,
        company_id=company_id,
        client_photo_id=idempotency_key,
        payload=payload,
    )
    return PhotoSyncOut.model_validate(result)


@router.post(
    "/photos/{photo_id}/confirm",
    response_model=PhotoOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def confirm_photo(
    photo_id: UUID,
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> PhotoOut:
    row = service.confirm_photo(session, storage, photo_id=photo_id)
    out = PhotoOut.model_validate(row)
    # Sincronizou → transmite na galeria da obra. `emit` é best-effort.
    emit(
        publisher,
        DomainEvent(
            channel=f"obra:{out.obra_id}:fotos",
            event=EVENT_FOTO_SINCRONIZADA,
            payload=out.model_dump(mode="json"),
        ),
    )
    return out


@router.get("/obras/{obra_id}/photos", response_model=PhotoPage)
def list_photos(
    obra_id: UUID,
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PhotoPage:
    items, next_cursor = service.list_photos(
        session, storage, obra_id=obra_id, cursor=cursor, limit=limit
    )
    return PhotoPage(items=[PhotoOut.model_validate(row) for row in items], next_cursor=next_cursor)
