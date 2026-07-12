"""Orquestrador dos agentes (B10.3).

Pipeline: intake → auth → intent → router → subagente → responder → audit.
Aqui em Python direto (o SPRINTS/CLAUDE.md preveem LangGraph `StateGraph`; o
grafo real seria plugado neste seam sem mudar o chamador — mesma estratégia das
integrações in-process). Consumido tanto pelo worker do WhatsApp quanto pelo
endpoint do painel (Assistente IA).

Enforcement de permissão/limite (B10.7) só se aplica ao canal WhatsApp
(`require_permission=True`): o painel é autenticado por JWT admin. Uma compra
negada NÃO levanta exceção — vira interação `erro` auditada + resposta educada
(o worker precisa responder algo ao usuário; o painel mostra a mensagem).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.llm import LLMClient
from app.modules.agentes import service
from app.modules.agentes.observability import get_agent_metrics
from app.modules.agentes.subagents import (
    SubagentResult,
    compras_subagent,
    orcamento_subagent,
)

_COMPRA_ROLES = ("solicitador", "aprovador")


@dataclass(frozen=True)
class OrchestratorResult:
    reply: str
    interaction: dict[str, Any]


def _authorize_compra(session: Session, *, whatsapp_number: str, cost_cents: int) -> str | None:
    """Retorna None se autorizado, ou o motivo da recusa (para auditar/responder)."""
    perm = service.get_permission(session, whatsapp_number=whatsapp_number)
    if perm is None or perm["role"] not in _COMPRA_ROLES:
        return "número sem permissão para registrar compras"
    daily = perm["daily_limit_cents"]
    if (
        daily
        and service.spend_cents(session, whatsapp_number=whatsapp_number, window="day") + cost_cents
        > daily
    ):
        return "limite diário de gasto excedido"
    monthly = perm["monthly_limit_cents"]
    if (
        monthly
        and service.spend_cents(session, whatsapp_number=whatsapp_number, window="month")
        + cost_cents
        > monthly
    ):
        return "limite mensal de gasto excedido"
    return None


def _saudacao() -> SubagentResult:
    return SubagentResult(
        agent="assistente",
        reply=(
            "Olá! Sou o assistente da Obrax. Posso consultar status de obras, "
            "resumos de orçamento e registrar solicitações de compra."
        ),
        action=None,
        obra_id=None,
    )


def _desconhecido() -> SubagentResult:
    return SubagentResult(
        agent="assistente",
        reply=(
            "Não consegui entender o pedido. Posso ajudar com status de obra, "
            "resumo de orçamento e solicitações de compra."
        ),
        action=None,
        obra_id=None,
    )


def process_message(
    session: Session,
    llm: LLMClient,
    *,
    company_id: str,
    whatsapp_number: str,
    command: str,
    require_permission: bool,
    agent_message_id: UUID | None = None,
) -> OrchestratorResult:
    started = time.perf_counter()
    metrics = get_agent_metrics()

    llm_result = llm.classify_intent(command)
    intent = llm_result.intent
    status_ = "ok"

    if intent == "criar_compra":
        recusa = (
            _authorize_compra(
                session, whatsapp_number=whatsapp_number, cost_cents=llm_result.cost_cents
            )
            if require_permission
            else None
        )
        if recusa is not None:
            outcome = SubagentResult(
                agent="compras", reply=f"Não autorizado: {recusa}.", action=None, obra_id=None
            )
            status_ = "erro"
        else:
            outcome = compras_subagent(session, message=command)
    elif intent in ("consulta_status", "consulta_orcamento"):
        outcome = orcamento_subagent(session, message=command, intent=intent)
    elif intent == "saudacao":
        outcome = _saudacao()
    else:
        outcome = _desconhecido()

    interaction = service.record_interaction(
        session,
        company_id=company_id,
        whatsapp_number=whatsapp_number,
        command=command,
        intent=intent,
        agent=outcome.agent,
        action=outcome.action,
        result=outcome.reply,
        obra_id=outcome.obra_id,
        cost_cents=llm_result.cost_cents,
        status_=status_,
        agent_message_id=agent_message_id,
    )

    metrics.observe_duration(time.perf_counter() - started)
    metrics.observe_interpretation(correct=intent != "desconhecido")
    return OrchestratorResult(reply=outcome.reply, interaction=interaction)
