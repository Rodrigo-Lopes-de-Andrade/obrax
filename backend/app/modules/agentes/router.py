"""Rotas do Módulo 3 (Sprint 10).

Dois grupos:
- Webhook Uazapi (`/webhook/uazapi`): não autenticado (valida HMAC), pré-tenant
  (usa `app_admin`), rate-limited, idempotente, enfileira e devolve ack rápido.
- Painel IA (`/ia/*` + `/feature-flags`): autenticado (JWT), sob RLS via `get_db`.
  Espelha o contrato consumido pelo frontend (lib/api/ia.ts).
"""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_admin_db, get_current_user, get_db, get_tenant, require_roles
from app.core.middleware import AuthContext
from app.integrations.agent_queue import AgentJob, AgentQueue, get_agent_queue
from app.integrations.llm import LLMClient, get_llm_client
from app.integrations.uazapi import InProcessRateLimiter, get_rate_limiter, verify_signature
from app.modules.agentes import orchestrator, service
from app.modules.agentes.schemas import (
    ChatMessageIn,
    ChatMessageOut,
    CopilotIn,
    CopilotSuggestionOut,
    InsightsOut,
    InteractionOut,
    InteractionPage,
    PermissionCreate,
    PermissionOut,
    PermissionPage,
    UazapiWebhookIn,
    WebhookAck,
)

router = APIRouter(tags=["agentes"])

_PERM_ROLES = require_roles("owner", "admin")


# ── Webhook Uazapi (B10.1) ─────────────────────────────────────────────────
@router.post("/webhook/uazapi", response_model=WebhookAck)
async def uazapi_webhook(
    request: Request,
    session: Session = Depends(get_admin_db),
    queue: AgentQueue = Depends(get_agent_queue),
    limiter: InProcessRateLimiter = Depends(get_rate_limiter),
) -> WebhookAck:
    raw = await request.body()
    if not verify_signature(
        raw_body=raw,
        signature=request.headers.get("x-uazapi-signature"),
        secret=settings.uazapi_webhook_secret,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="assinatura inválida")
    try:
        payload = UazapiWebhookIn.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payload inválido"
        ) from exc

    if not limiter.allow(payload.from_number, now=time.time()):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit excedido"
        )

    company_id = service.resolve_company_by_number(session, whatsapp_number=payload.from_number)
    if company_id is None:
        # Número não autorizado por nenhum tenant: ack sem enfileirar.
        return WebhookAck(status="ignored", message_id=payload.message_id)

    msg_id, is_new = service.insert_message(
        session,
        company_id=company_id,
        message_id=payload.message_id,
        from_number=payload.from_number,
        content=payload.text,
    )
    if not is_new or msg_id is None:
        return WebhookAck(status="duplicate", message_id=payload.message_id)

    queue.enqueue(AgentJob(company_id=company_id, agent_message_id=str(msg_id)))
    return WebhookAck(status="queued", message_id=payload.message_id)


# ── Feature flags ─────────────────────────────────────────────────────────
@router.get("/feature-flags", response_model=dict[str, bool])
def feature_flags(_auth: AuthContext = Depends(get_current_user)) -> dict[str, bool]:
    # MVP: liga o Módulo 3 para todos os tenants autenticados. Em produção lê o
    # tier (PostHog `ia-module-enabled`, docs/CLAUDE.md).
    return {"ia-module-enabled": True}


# ── Assistente (F10.1) ────────────────────────────────────────────────────
@router.get("/ia/assistente/mensagens", response_model=list[ChatMessageOut])
def assistente_thread(session: Session = Depends(get_db)) -> list[ChatMessageOut]:
    return [ChatMessageOut(**m) for m in service.assistente_thread(session)]


@router.post(
    "/ia/assistente/mensagens",
    response_model=ChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def assistente_enviar(
    payload: ChatMessageIn,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> ChatMessageOut:
    result = orchestrator.process_message(
        session,
        llm,
        company_id=company_id,
        whatsapp_number=service.PAINEL_NUMERO,
        command=payload.content,
        require_permission=False,
    )
    it = result.interaction
    return ChatMessageOut(
        id=f"{it['id']}-a", role="assistant", content=result.reply, created_at=it["created_at"]
    )


# ── Auditoria (F10.2 / B10.6) ─────────────────────────────────────────────
@router.get("/ia/interacoes", response_model=InteractionPage)
def listar_interacoes(
    session: Session = Depends(get_db),
    obra_id: UUID | None = Query(default=None),
    agent: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> InteractionPage:
    items, next_cursor = service.list_interactions(
        session, obra_id=obra_id, agent=agent, cursor=cursor, limit=limit
    )
    return InteractionPage(items=[InteractionOut(**r) for r in items], next_cursor=next_cursor)


@router.post("/ia/interacoes/{interaction_id}/reverter", response_model=InteractionOut)
def reverter_interacao(
    interaction_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> InteractionOut:
    row = service.revert_interaction(
        session, interaction_id=interaction_id, reverted_by=auth.user_id
    )
    return InteractionOut(**row)


# ── Permissões (F10.3 / B10.7) ────────────────────────────────────────────
@router.get("/ia/permissoes", response_model=PermissionPage)
def listar_permissoes(session: Session = Depends(get_db)) -> PermissionPage:
    rows = service.list_permissions(session)
    return PermissionPage(items=[PermissionOut.model_validate(r) for r in rows], next_cursor=None)


@router.post(
    "/ia/permissoes",
    response_model=PermissionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_PERM_ROLES)],
)
def criar_permissao(
    payload: PermissionCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> PermissionOut:
    row = service.create_permission(session, company_id=company_id, payload=payload)
    return PermissionOut.model_validate(row)


@router.delete(
    "/ia/permissoes/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_PERM_ROLES)],
)
def remover_permissao(permission_id: UUID, session: Session = Depends(get_db)) -> None:
    service.delete_permission(session, permission_id=permission_id)


# ── Copilot (F10.4) ───────────────────────────────────────────────────────
@router.post("/ia/copilot/sugerir", response_model=list[CopilotSuggestionOut])
def copilot_sugerir(
    payload: CopilotIn, _auth: AuthContext = Depends(get_current_user)
) -> list[CopilotSuggestionOut]:
    return [CopilotSuggestionOut(**s) for s in service.copilot_suggest(payload.descricao)]


# ── Insights (F10.5) ──────────────────────────────────────────────────────
@router.get("/ia/insights", response_model=InsightsOut)
def ia_insights(session: Session = Depends(get_db)) -> InsightsOut:
    data = service.insights(session)
    return InsightsOut(
        acoes_ultima_semana=data["acoes_ultima_semana"],
        economia_tempo_min=data["economia_tempo_min"],
        taxa_sucesso=data["taxa_sucesso"],
        ultimas_acoes=[InteractionOut(**r) for r in data["ultimas_acoes"]],
    )
