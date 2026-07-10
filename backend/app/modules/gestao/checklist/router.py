"""Router do checklist de campo (B7.2, US-16).

Montado sem prefixo (paths absolutos): listar/criar aninhados na obra
(`/obras/{id}/checklist`); toggle/excluir planos por id (`/checklist/{id}`) —
mesmo padrão de documentos/orçamentos. Isolamento por empresa via RLS no
`get_db`.

Escrita (criar / toggle / excluir): owner/admin/gestor/**campo** — marcar itens
é a ação de campo. Leitura: qualquer usuário do tenant.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.modules.gestao.checklist import service
from app.modules.gestao.checklist.schemas import (
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    ChecklistPage,
)

router = APIRouter(tags=["checklist"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor", "campo")


@router.get("/obras/{obra_id}/checklist", response_model=ChecklistPage)
def list_checklist(
    obra_id: UUID,
    session: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
) -> ChecklistPage:
    items, next_cursor = service.list_items(session, obra_id=obra_id, cursor=cursor, limit=limit)
    return ChecklistPage(
        items=[ChecklistItemOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.post(
    "/obras/{obra_id}/checklist",
    response_model=ChecklistItemOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def create_checklist_item(
    obra_id: UUID,
    payload: ChecklistItemCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> ChecklistItemOut:
    row = service.create_item(session, company_id=company_id, obra_id=obra_id, payload=payload)
    return ChecklistItemOut.model_validate(row)


@router.patch(
    "/checklist/{item_id}",
    response_model=ChecklistItemOut,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_checklist_item(
    item_id: UUID,
    payload: ChecklistItemUpdate,
    session: Session = Depends(get_db),
) -> ChecklistItemOut:
    row = service.update_item(session, item_id=item_id, payload=payload)
    return ChecklistItemOut.model_validate(row)


@router.delete(
    "/checklist/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_checklist_item(item_id: UUID, session: Session = Depends(get_db)) -> None:
    service.delete_item(session, item_id=item_id)
