"""Router de documentos — GED do Módulo 1 (B3.2 upload, B3.3 CRUD; US-04/US-06).

Montado sem prefixo (paths absolutos): endpoints aninhados na obra
(`/obras/{id}/documentos`) e planos (`/documentos/{id}`), conforme
docs/ESPEC.md § 6. Leitura: qualquer usuário autenticado do tenant. Escrita
(create/confirm/patch/delete): `owner`/`admin`/`gestor`. Isolamento por empresa
via RLS no `get_db` — nenhum endpoint filtra `company_id` na mão.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.integrations.storage import StorageClient, get_storage_client
from app.modules.gestao.documentos import service
from app.modules.gestao.documentos.schemas import (
    DocumentoCreate,
    DocumentoOut,
    DocumentoPage,
    DocumentoUpdate,
    DocumentoUploadOut,
)

router = APIRouter(tags=["documentos"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "/obras/{obra_id}/documentos",
    response_model=DocumentoUploadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_documento(
    obra_id: UUID,
    payload: DocumentoCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> DocumentoUploadOut:
    result = service.create_upload(
        session,
        storage,
        company_id=company_id,
        obra_id=obra_id,
        uploaded_by=auth.user_id,
        payload=payload,
    )
    return DocumentoUploadOut.model_validate(result)


@router.get("/obras/{obra_id}/documentos", response_model=DocumentoPage)
def list_documentos(
    obra_id: UUID,
    session: Session = Depends(get_db),
    categoria: str | None = Query(default=None),
    search: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> DocumentoPage:
    items, next_cursor = service.list_documentos(
        session, obra_id=obra_id, categoria=categoria, search=search, cursor=cursor, limit=limit
    )
    return DocumentoPage(
        items=[DocumentoOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.post(
    "/documentos/{documento_id}/confirm",
    response_model=DocumentoOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def confirm_documento(
    documento_id: UUID,
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> DocumentoOut:
    row = service.confirm_upload(session, storage, documento_id=documento_id)
    return DocumentoOut.model_validate(row)


@router.patch(
    "/documentos/{documento_id}",
    response_model=DocumentoOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_documento(
    documento_id: UUID,
    payload: DocumentoUpdate,
    session: Session = Depends(get_db),
) -> DocumentoOut:
    row = service.update_documento(session, documento_id=documento_id, payload=payload)
    return DocumentoOut.model_validate(row)


@router.delete(
    "/documentos/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_documento(documento_id: UUID, session: Session = Depends(get_db)) -> None:
    service.soft_delete_documento(session, documento_id)
