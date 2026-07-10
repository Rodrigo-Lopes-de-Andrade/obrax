"""Router de ocorrências de campo (B8.4, US-18).

Montado sem prefixo (paths absolutos): create/list aninhados na obra
(`/obras/{id}/ocorrencias`) e get/patch planos (`/ocorrencias/{id}`) — mesmo
padrão de documentos/tickets. Isolamento por empresa via RLS no `get_db`.

Escrita (registrar / mudar status): owner/admin/gestor/**campo** — registrar
ocorrência é ação de campo. Leitura: qualquer usuário do tenant.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.modules.gestao.ocorrencias import service
from app.modules.gestao.ocorrencias.schemas import (
    OcorrenciaCreate,
    OcorrenciaOut,
    OcorrenciaPage,
    OcorrenciaUpdate,
)

router = APIRouter(tags=["ocorrencias"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor", "campo")


@router.post(
    "/obras/{obra_id}/ocorrencias",
    response_model=OcorrenciaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_ocorrencia(
    obra_id: UUID,
    payload: OcorrenciaCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OcorrenciaOut:
    row = service.create_ocorrencia(
        session,
        company_id=company_id,
        obra_id=obra_id,
        created_by=auth.user_id,
        payload=payload,
    )
    return OcorrenciaOut.model_validate(row)


@router.get("/obras/{obra_id}/ocorrencias", response_model=OcorrenciaPage)
def list_ocorrencias(
    obra_id: UUID,
    session: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> OcorrenciaPage:
    items, next_cursor = service.list_ocorrencias(
        session, obra_id=obra_id, cursor=cursor, limit=limit
    )
    return OcorrenciaPage(
        items=[OcorrenciaOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.get("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def get_ocorrencia(ocorrencia_id: UUID, session: Session = Depends(get_db)) -> OcorrenciaOut:
    return OcorrenciaOut.model_validate(service.get_ocorrencia(session, ocorrencia_id))


@router.patch(
    "/ocorrencias/{ocorrencia_id}",
    response_model=OcorrenciaOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_ocorrencia(
    ocorrencia_id: UUID,
    payload: OcorrenciaUpdate,
    session: Session = Depends(get_db),
) -> OcorrenciaOut:
    row = service.update_ocorrencia(session, ocorrencia_id=ocorrencia_id, payload=payload)
    return OcorrenciaOut.model_validate(row)
