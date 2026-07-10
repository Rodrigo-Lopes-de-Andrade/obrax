"""Router do portal do cliente (B9.2 leitura, B9.3 aprovação; US-19/US-20).

Montado sem prefixo (paths absolutos), como documentos/tickets. Dois grupos:
- `POST /obras/{id}/portal-link` — ação de admin (emite o link); autenticada
  pelo JWT de acesso (get_db), restrita a owner/admin/gestor.
- `GET/POST /portal/...` — acesso do cliente; autenticado pelo token do portal
  no path (get_portal_db). Leitura read-only + a decisão sobre o orçamento.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.integrations.notifications import Notifier, get_notifier
from app.integrations.storage import StorageClient, get_storage_client
from app.modules.portal import service
from app.modules.portal.deps import PortalContext, get_portal_context, get_portal_db
from app.modules.portal.schemas import (
    PortalAprovacaoIn,
    PortalLinkOut,
    PortalObra,
    PortalOrcamento,
)

router = APIRouter(tags=["portal"])

_LINK_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "/obras/{obra_id}/portal-link",
    response_model=PortalLinkOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_LINK_ROLES)],
)
def gerar_portal_link(
    obra_id: UUID,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> PortalLinkOut:
    """Emite o link do portal (token de 30 min) para o cliente da obra."""
    out = service.mint_portal_link(session, company_id=company_id, obra_id=obra_id)
    return PortalLinkOut.model_validate(out)


@router.get("/portal/obras/{token}", response_model=PortalObra)
def portal_obra(
    ctx: PortalContext = Depends(get_portal_context),
    session: Session = Depends(get_portal_db),
    storage: StorageClient = Depends(get_storage_client),
) -> PortalObra:
    """Timeline read-only da obra para o cliente — sem dados financeiros."""
    out = service.get_portal_obra(session, storage, obra_id=ctx.obra_id)
    return PortalObra.model_validate(out)


@router.get("/portal/orcamentos/{token}", response_model=PortalOrcamento)
def portal_orcamento(
    ctx: PortalContext = Depends(get_portal_context),
    session: Session = Depends(get_portal_db),
    storage: StorageClient = Depends(get_storage_client),
) -> PortalOrcamento:
    """Orçamento vigente da obra para o cliente aprovar (preço + PDF)."""
    out = service.get_portal_orcamento(session, storage, obra_id=ctx.obra_id)
    return PortalOrcamento.model_validate(out)


@router.post("/portal/orcamentos/{token}/aprovar", response_model=PortalOrcamento)
def portal_aprovar(
    payload: PortalAprovacaoIn,
    ctx: PortalContext = Depends(get_portal_context),
    session: Session = Depends(get_portal_db),
    storage: StorageClient = Depends(get_storage_client),
    notifier: Notifier = Depends(get_notifier),
) -> PortalOrcamento:
    out = service.decide_orcamento(
        session,
        storage,
        notifier,
        company_id=str(ctx.company_id),
        obra_id=ctx.obra_id,
        decisao="aprovado",
        payload=payload,
    )
    return PortalOrcamento.model_validate(out)


@router.post("/portal/orcamentos/{token}/rejeitar", response_model=PortalOrcamento)
def portal_rejeitar(
    payload: PortalAprovacaoIn,
    ctx: PortalContext = Depends(get_portal_context),
    session: Session = Depends(get_portal_db),
    storage: StorageClient = Depends(get_storage_client),
    notifier: Notifier = Depends(get_notifier),
) -> PortalOrcamento:
    out = service.decide_orcamento(
        session,
        storage,
        notifier,
        company_id=str(ctx.company_id),
        obra_id=ctx.obra_id,
        decisao="rejeitado",
        payload=payload,
    )
    return PortalOrcamento.model_validate(out)
