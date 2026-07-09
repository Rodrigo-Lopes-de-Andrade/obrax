"""Router de documentos — upload em duas etapas (B3.2, US-04/US-05).

Montado sem prefixo (paths absolutos): o create é aninhado na obra
(`/obras/{id}/documentos`) e o confirm é plano (`/documentos/{id}/confirm`),
conforme docs/ESPEC.md § 6. Escrita restrita a `owner`/`admin`/`gestor`;
isolamento por empresa via RLS no `get_db`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.integrations.storage import StorageClient, get_storage_client
from app.modules.gestao.documentos import service
from app.modules.gestao.documentos.schemas import (
    DocumentoCreate,
    DocumentoOut,
    DocumentoUploadOut,
)

router = APIRouter()

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "/obras/{obra_id}/documentos",
    response_model=DocumentoUploadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
    tags=["documentos"],
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


@router.post(
    "/documentos/{documento_id}/confirm",
    response_model=DocumentoOut,
    dependencies=[Depends(_WRITE_ROLES)],
    tags=["documentos"],
)
def confirm_documento(
    documento_id: UUID,
    session: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> DocumentoOut:
    row = service.confirm_upload(session, storage, documento_id=documento_id)
    return DocumentoOut.model_validate(row)
