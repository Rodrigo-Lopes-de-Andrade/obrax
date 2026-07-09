"""Router dos itens da EAP (B5.4, US-12).

Paths absolutos aninhados na versão (`/orcamentos/versoes/{vid}/itens*`) ou no
item (`/orcamentos/itens/{id}*`). Toda mutação recalcula e devolve a árvore
inteira (EapTree). Escrita: owner/admin/gestor/orcamentista; leitura: qualquer
usuário do tenant. Isolamento por RLS no `get_db`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.modules.orcamento.importers import xlsx_importer
from app.modules.orcamento.schemas import (
    EapTree,
    ItensBulkCreate,
    ItemUpdate,
    PrecificacaoUpdate,
    ReorderRequest,
)
from app.modules.orcamento.services import itens as service

router = APIRouter(tags=["orcamento-itens"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor", "orcamentista")

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB (F5.5)


@router.get("/orcamentos/versoes/{versao_id}/itens", response_model=EapTree)
def get_tree(versao_id: UUID, session: Session = Depends(get_db)) -> EapTree:
    return service.tree_model(service.get_tree(session, versao_id))


@router.post(
    "/orcamentos/versoes/{versao_id}/itens/bulk",
    response_model=EapTree,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def bulk_create(
    versao_id: UUID,
    payload: ItensBulkCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> EapTree:
    data = service.bulk_create(
        session, company_id=company_id, versao_id=versao_id, novos=payload.itens
    )
    return service.tree_model(data)


@router.patch(
    "/orcamentos/itens/{item_id}",
    response_model=EapTree,
    dependencies=[Depends(_WRITE_ROLES)],
)
def update_item(item_id: UUID, payload: ItemUpdate, session: Session = Depends(get_db)) -> EapTree:
    return service.tree_model(service.update_item(session, item_id=item_id, patch=payload))


@router.delete(
    "/orcamentos/itens/{item_id}",
    response_model=EapTree,
    dependencies=[Depends(_WRITE_ROLES)],
)
def delete_item(item_id: UUID, session: Session = Depends(get_db)) -> EapTree:
    return service.tree_model(service.delete_item(session, item_id=item_id))


@router.post(
    "/orcamentos/itens/{item_id}/duplicar",
    response_model=EapTree,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def duplicate_item(
    item_id: UUID,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> EapTree:
    data = service.duplicate_item(session, company_id=company_id, item_id=item_id)
    return service.tree_model(data)


@router.put(
    "/orcamentos/versoes/{versao_id}/itens/ordem",
    response_model=EapTree,
    dependencies=[Depends(_WRITE_ROLES)],
)
def reorder(
    versao_id: UUID, payload: ReorderRequest, session: Session = Depends(get_db)
) -> EapTree:
    return service.tree_model(service.reorder(session, versao_id=versao_id, ordem=payload.itens))


@router.put(
    "/orcamentos/versoes/{versao_id}/precificacao",
    response_model=EapTree,
    dependencies=[Depends(_WRITE_ROLES)],
)
def set_precificacao(
    versao_id: UUID, payload: PrecificacaoUpdate, session: Session = Depends(get_db)
) -> EapTree:
    data = service.set_precificacao(
        session,
        versao_id=versao_id,
        markup_global=payload.markup_global,
        taxa_adm=payload.taxa_adm,
    )
    return service.tree_model(data)


# Path de 3 segmentos: não colide com GET /orcamentos/{id} (2 segmentos).
@router.get("/orcamentos/importar/modelo")
def download_template(_: AuthContext = Depends(get_current_user)) -> Response:
    """Modelo XLSX da EAP para preencher e importar (F5.5)."""
    return Response(
        content=xlsx_importer.build_template(),
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": 'attachment; filename="modelo_orcamento.xlsx"'},
    )


@router.post(
    "/orcamentos/versoes/{versao_id}/importar-planilha",
    response_model=EapTree,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
async def importar_planilha(
    versao_id: UUID,
    arquivo: UploadFile = File(...),
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> EapTree:
    content = await arquivo.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="arquivo excede 30MB",
        )
    try:
        parsed = xlsx_importer.parse_xlsx(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if parsed.erros:
        # Erros linha-a-linha: {linha, campo, mensagem} — a UI mostra cada um.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"erros": parsed.erros},
        )
    data = service.importar_hierarquia(
        session, company_id=company_id, versao_id=versao_id, linhas=parsed.linhas
    )
    return service.tree_model(data)
