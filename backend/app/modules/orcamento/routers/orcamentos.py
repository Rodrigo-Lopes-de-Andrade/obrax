"""Router de orçamentos — CRUD + status (B5.3, US-11).

Montado sem prefixo (paths absolutos): create aninhado na obra
(`/obras/{id}/orcamentos`) e os demais planos (`/orcamentos*`), conforme o
padrão de tickets/documentos. Isolamento por empresa via RLS no `get_db`.

Escrita (criar / mudar status / excluir): owner/admin/gestor/orcamentista.
Leitura: qualquer usuário do tenant (a RLS já limita ao tenant).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.modules.orcamento.schemas import (
    OrcamentoCreate,
    OrcamentoDetail,
    OrcamentoOut,
    OrcamentoPage,
    OrcamentoStatusUpdate,
)
from app.modules.orcamento.services import orcamentos as service

router = APIRouter(tags=["orcamentos"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor", "orcamentista")


@router.post(
    "/obras/{obra_id}/orcamentos",
    response_model=OrcamentoDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_orcamento(
    obra_id: UUID,
    payload: OrcamentoCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OrcamentoDetail:
    row = service.create_orcamento(
        session,
        company_id=company_id,
        obra_id=obra_id,
        created_by=auth.user_id,
        payload=payload,
    )
    return OrcamentoDetail.model_validate(row)


@router.get("/orcamentos", response_model=OrcamentoPage)
def list_orcamentos(
    session: Session = Depends(get_db),
    obra_id: UUID | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> OrcamentoPage:
    items, next_cursor = service.list_orcamentos(
        session, obra_id=obra_id, cursor=cursor, limit=limit
    )
    return OrcamentoPage(
        items=[OrcamentoOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.get("/orcamentos/{orcamento_id}", response_model=OrcamentoDetail)
def get_orcamento(orcamento_id: UUID, session: Session = Depends(get_db)) -> OrcamentoDetail:
    return OrcamentoDetail.model_validate(service.get_orcamento(session, orcamento_id))


@router.patch(
    "/orcamentos/{orcamento_id}/status",
    response_model=OrcamentoDetail,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_status(
    orcamento_id: UUID,
    payload: OrcamentoStatusUpdate,
    session: Session = Depends(get_db),
) -> OrcamentoDetail:
    row = service.update_status(session, orcamento_id=orcamento_id, new_status=payload.status)
    return OrcamentoDetail.model_validate(row)


@router.delete(
    "/orcamentos/{orcamento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_orcamento(orcamento_id: UUID, session: Session = Depends(get_db)) -> None:
    service.soft_delete_orcamento(session, orcamento_id)
