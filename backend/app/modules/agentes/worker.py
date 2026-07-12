"""Worker de processamento da fila `agent.process` (B10.2/B10.3).

Lê um lote da fila, processa cada mensagem pelo orquestrador e confirma (ack) ou
devolve para retry (fail, backoff 30s/60s/120s até dead-letter). Cada job carrega
seu `company_id`; o worker abre uma sessão `app_user` e seta a GUC do tenant por
job (isolamento RLS), como o `get_db` faz por request.

No MVP não há daemon/arq rodando (sem Redis): `run_once` é a unidade
testável/agendável — um scheduler (arq/cron) chamaria em loop em produção.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import AppUserSessionLocal
from app.integrations.agent_queue import AgentQueue
from app.integrations.llm import LLMClient
from app.integrations.uazapi import UazapiClient
from app.modules.agentes import orchestrator, service

logger = logging.getLogger("app.agent_worker")


def _process_one(
    session: Session,
    llm: LLMClient,
    uazapi: UazapiClient,
    *,
    company_id: str,
    agent_message_id: UUID,
) -> None:
    """Processa uma mensagem já persistida, dentro de uma sessão com o tenant
    setado. Responde ao usuário via Uazapi (best-effort)."""
    row = (
        session.execute(
            text("SELECT whatsapp_number, content FROM agent_message WHERE id = :id"),
            {"id": agent_message_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return
    service.mark_message(session, message_id=agent_message_id, new_status="processando")
    result = orchestrator.process_message(
        session,
        llm,
        company_id=company_id,
        whatsapp_number=row["whatsapp_number"],
        command=row["content"],
        require_permission=True,
        agent_message_id=agent_message_id,
    )
    service.mark_message(session, message_id=agent_message_id, new_status="concluido")
    uazapi.send_text(to=row["whatsapp_number"], text=result.reply)


def run_once(llm: LLMClient, queue: AgentQueue, uazapi: UazapiClient, *, batch: int = 10) -> int:
    """Consome um lote da fila. Retorna quantos jobs foram processados com sucesso.
    Cada job roda em sua própria transação `app_user` com a GUC do tenant."""
    jobs = queue.poll(batch=batch)
    ok = 0
    for job in jobs:
        session = AppUserSessionLocal()
        try:
            session.execute(
                text("SELECT set_config('app.company_id', :cid, true)"),
                {"cid": job.company_id},
            )
            _process_one(
                session,
                llm,
                uazapi,
                company_id=job.company_id,
                agent_message_id=UUID(job.agent_message_id),
            )
            session.commit()
            queue.ack(job)
            ok += 1
        except Exception:
            session.rollback()
            logger.warning("falha ao processar job %s", job.agent_message_id, exc_info=True)
            _mark_error(job.company_id, UUID(job.agent_message_id))
            queue.fail(job)
        finally:
            session.close()
    return ok


def _mark_error(company_id: str, agent_message_id: UUID) -> None:
    """Carimba a mensagem como `erro` numa transação própria (a de processamento
    já sofreu rollback)."""
    session = AppUserSessionLocal()
    try:
        session.execute(
            text("SELECT set_config('app.company_id', :cid, true)"), {"cid": company_id}
        )
        service.mark_message(
            session, message_id=agent_message_id, new_status="erro", error="processamento falhou"
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
