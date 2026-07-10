"""Router dos pedidos LGPD (B9.4 export; US-21). Prefixo `/lgpd`.

Dado sensível: restrito a owner/admin. O export monta o ZIP de forma síncrona
(sem fila) e devolve o link de download já assinado; o mesmo link pode ser
re-obtido em `/lgpd/requests/{id}/download` enquanto dentro dos 7 dias.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.integrations.storage import StorageClient, get_storage_client
from app.modules.lgpd import service
from app.modules.lgpd.schemas import (
    LgpdDownloadOut,
    LgpdRequestCreate,
    LgpdRequestOut,
    LgpdRequestPage,
)

router = APIRouter(prefix="/lgpd", tags=["lgpd"])

_LGPD_ROLES = require_roles("owner", "admin")


@router.post(
    "/requests",
    response_model=LgpdRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_LGPD_ROLES)],
)
def criar_pedido(
    payload: LgpdRequestCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> LgpdRequestOut:
    out = service.create_request(
        session, storage, company_id=company_id, requested_by=auth.user_id, payload=payload
    )
    return LgpdRequestOut.model_validate(out)


@router.get("/requests", response_model=LgpdRequestPage, dependencies=[Depends(_LGPD_ROLES)])
def listar_pedidos(
    session: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> LgpdRequestPage:
    items, next_cursor = service.list_requests(session, cursor=cursor, limit=limit)
    return LgpdRequestPage(
        items=[LgpdRequestOut.model_validate(r) for r in items], next_cursor=next_cursor
    )


@router.get(
    "/requests/{request_id}/download",
    response_model=LgpdDownloadOut,
    dependencies=[Depends(_LGPD_ROLES)],
)
def baixar_export(
    request_id: UUID,
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> LgpdDownloadOut:
    out = service.get_download(session, storage, request_id=request_id)
    return LgpdDownloadOut.model_validate(out)
