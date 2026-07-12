"""Acesso a dados + regras do Módulo 3 (B10.2/B10.6/B10.7 e painel IA).

Roda sob `get_db` (role `app_user`, RLS ativa) — as queries já saem escopadas ao
tenant; os INSERTs passam `company_id` explícito (policy WITH CHECK). SQL cru via
`text()`, no mesmo estilo dos demais módulos (ex.: lgpd/service.py).
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.agentes.schemas import PermissionCreate

# Painel do Assistente IA (F10.1): interações web usam este marcador em
# `whatsapp_number` para não se misturarem à trilha do WhatsApp na reconstrução
# do thread.
PAINEL_NUMERO = "painel"

_INTERACTION_SELECT = (
    "SELECT i.id, i.whatsapp_number, i.command, i.intent, i.agent, i.action, "
    "       i.result, i.status, i.cost_cents, i.obra_id, o.codigo AS obra_codigo, "
    "       i.reverted_at, i.created_at "
    "FROM agent_interaction i "
    "LEFT JOIN obras o ON o.id = i.obra_id "
)


# ── Permissões (B10.7) ────────────────────────────────────────────────────
_PERMISSION_COLUMNS = (
    "id, whatsapp_number, role, daily_limit_cents, monthly_limit_cents, created_at"
)


def list_permissions(session: Session) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            text(f"SELECT {_PERMISSION_COLUMNS} FROM ai_permission ORDER BY id DESC LIMIT 100")
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def create_permission(
    session: Session, *, company_id: str, payload: PermissionCreate
) -> dict[str, Any]:
    """Upsert: um papel por número por tenant (UNIQUE company_id, whatsapp_number)."""
    row = (
        session.execute(
            text(
                "INSERT INTO ai_permission "
                "(company_id, whatsapp_number, role, daily_limit_cents, monthly_limit_cents) "
                "VALUES (:c, :num, :role, :daily, :monthly) "
                "ON CONFLICT (company_id, whatsapp_number) DO UPDATE SET "
                "  role = EXCLUDED.role, "
                "  daily_limit_cents = EXCLUDED.daily_limit_cents, "
                "  monthly_limit_cents = EXCLUDED.monthly_limit_cents, "
                "  updated_at = now() "
                f"RETURNING {_PERMISSION_COLUMNS}"
            ),
            {
                "c": company_id,
                "num": payload.whatsapp_number.strip(),
                "role": payload.role,
                "daily": payload.daily_limit_cents,
                "monthly": payload.monthly_limit_cents,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def delete_permission(session: Session, *, permission_id: uuid.UUID) -> None:
    # RETURNING id para detectar inexistência (rowcount não é tipado no Result).
    deleted = (
        session.execute(
            text("DELETE FROM ai_permission WHERE id = :id RETURNING id"), {"id": permission_id}
        )
        .mappings()
        .first()
    )
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="permissão não encontrada"
        )


def get_permission(session: Session, *, whatsapp_number: str) -> dict[str, Any] | None:
    row = (
        session.execute(
            text(f"SELECT {_PERMISSION_COLUMNS} FROM ai_permission WHERE whatsapp_number = :num"),
            {"num": whatsapp_number},
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def spend_cents(session: Session, *, whatsapp_number: str, window: Literal["day", "month"]) -> int:
    """Soma `cost_cents` das interações do número na janela (dia/mês) corrente —
    base do enforcement de limite de gasto (B10.7)."""
    interval = "1 day" if window == "day" else "30 days"
    total = session.execute(
        text(
            "SELECT COALESCE(SUM(cost_cents), 0) FROM agent_interaction "
            "WHERE whatsapp_number = :num AND created_at > now() - CAST(:iv AS interval)"
        ),
        {"num": whatsapp_number, "iv": interval},
    ).scalar_one()
    return int(total)


def resolve_company_by_number(session: Session, *, whatsapp_number: str) -> str | None:
    """Descobre o tenant dono de um número de WhatsApp (B10.1). PRÉ-TENANT: o
    webhook não é autenticado, então isto roda sob `app_admin` (BYPASSRLS) para
    varrer `ai_permission` de todos os tenants — mesmo padrão do login/convite
    (ver app/core/deps.py get_admin_db). Número não autorizado → None."""
    row = (
        session.execute(
            text("SELECT company_id FROM ai_permission WHERE whatsapp_number = :num LIMIT 1"),
            {"num": whatsapp_number},
        )
        .mappings()
        .first()
    )
    return str(row["company_id"]) if row is not None else None


# ── Mensagens / fila (B10.2) ──────────────────────────────────────────────
def insert_message(
    session: Session, *, company_id: str, message_id: str, from_number: str, content: str
) -> tuple[uuid.UUID | None, bool]:
    """Insere a mensagem do webhook de forma idempotente (UNIQUE company_id,
    message_id). Retorna (id, is_new): is_new=False quando é reentrega."""
    row = (
        session.execute(
            text(
                "INSERT INTO agent_message (company_id, message_id, whatsapp_number, content) "
                "VALUES (:c, :mid, :num, :content) "
                "ON CONFLICT (company_id, message_id) DO NOTHING "
                "RETURNING id"
            ),
            {"c": company_id, "mid": message_id, "num": from_number, "content": content},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None, False
    return row["id"], True


def mark_message(
    session: Session,
    *,
    message_id: uuid.UUID,
    new_status: Literal["processando", "concluido", "erro"],
    error: str | None = None,
) -> None:
    session.execute(
        text(
            "UPDATE agent_message SET status = :st, error_detail = :err, "
            "processed_at = CASE WHEN :st IN ('concluido','erro') THEN now() ELSE processed_at END "
            "WHERE id = :id"
        ),
        {"st": new_status, "err": error, "id": message_id},
    )


# ── Interações / auditoria (B10.6) ────────────────────────────────────────
def record_interaction(
    session: Session,
    *,
    company_id: str,
    whatsapp_number: str,
    command: str,
    intent: str | None,
    agent: str | None,
    action: str | None,
    result: str | None,
    obra_id: uuid.UUID | None,
    cost_cents: int,
    status_: str = "ok",
    agent_message_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                "INSERT INTO agent_interaction "
                "(company_id, agent_message_id, obra_id, whatsapp_number, command, intent, "
                " agent, action, result, status, cost_cents) "
                "VALUES (:c, :amid, :obra, :num, :cmd, :intent, :agent, :action, :result, "
                " :st, :cost) RETURNING id"
            ),
            {
                "c": company_id,
                "amid": agent_message_id,
                "obra": obra_id,
                "num": whatsapp_number,
                "cmd": command,
                "intent": intent,
                "agent": agent,
                "action": action,
                "result": result,
                "st": status_,
                "cost": cost_cents,
            },
        )
        .mappings()
        .one()
    )
    return _get_interaction(session, interaction_id=row["id"])


def _get_interaction(session: Session, *, interaction_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(text(_INTERACTION_SELECT + "WHERE i.id = :id"), {"id": interaction_id})
        .mappings()
        .one()
    )
    return dict(row)


def list_interactions(
    session: Session,
    *,
    obra_id: uuid.UUID | None,
    agent: str | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    if cursor is not None:
        try:
            uuid.UUID(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cursor inválido"
            ) from exc
    rows = (
        session.execute(
            text(
                _INTERACTION_SELECT
                + "WHERE (CAST(:cursor AS uuid) IS NULL OR i.id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:obra AS uuid) IS NULL OR i.obra_id = CAST(:obra AS uuid)) "
                "  AND (:agent IS NULL OR i.agent = :agent) "
                "ORDER BY i.id DESC LIMIT :limit_plus_one"
            ),
            {
                "cursor": cursor,
                "obra": str(obra_id) if obra_id else None,
                "agent": agent,
                "limit_plus_one": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def revert_interaction(
    session: Session, *, interaction_id: uuid.UUID, reverted_by: uuid.UUID
) -> dict[str, Any]:
    """Marca a interação como revertida (US-22). Só ações com efeito
    (`action IS NOT NULL`) e ainda não revertidas."""
    row = (
        session.execute(
            text("SELECT action, reverted_at FROM agent_interaction WHERE id = :id"),
            {"id": interaction_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="interação não encontrada"
        )
    if row["action"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="interação de consulta não é reversível"
        )
    if row["reverted_at"] is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ação já revertida")
    session.execute(
        text(
            "UPDATE agent_interaction SET status = 'revertido', reverted_at = now(), "
            "reverted_by = :by WHERE id = :id"
        ),
        {"by": reverted_by, "id": interaction_id},
    )
    return _get_interaction(session, interaction_id=interaction_id)


# ── Assistente / thread (F10.1) ───────────────────────────────────────────
def assistente_thread(session: Session) -> list[dict[str, Any]]:
    """Reconstrói o histórico do painel: cada interação vira uma mensagem do
    usuário (command) + uma do assistente (result), em ordem cronológica."""
    rows = (
        session.execute(
            text(
                "SELECT id, command, result, created_at FROM agent_interaction "
                "WHERE whatsapp_number = :num ORDER BY id ASC LIMIT 100"
            ),
            {"num": PAINEL_NUMERO},
        )
        .mappings()
        .all()
    )
    thread: list[dict[str, Any]] = []
    for r in rows:
        thread.append(
            {
                "id": f"{r['id']}-u",
                "role": "user",
                "content": r["command"],
                "created_at": r["created_at"],
            }
        )
        thread.append(
            {
                "id": f"{r['id']}-a",
                "role": "assistant",
                "content": r["result"] or "",
                "created_at": r["created_at"],
            }
        )
    return thread


# ── Insights (F10.5) ──────────────────────────────────────────────────────
def insights(session: Session) -> dict[str, Any]:
    semana = session.execute(
        text("SELECT COUNT(*) FROM agent_interaction WHERE created_at > now() - interval '7 days'")
    ).scalar_one()
    total = session.execute(text("SELECT COUNT(*) FROM agent_interaction")).scalar_one()
    ok = session.execute(
        text("SELECT COUNT(*) FROM agent_interaction WHERE status <> 'erro'")
    ).scalar_one()
    ultimas_rows = (
        session.execute(text(_INTERACTION_SELECT + "ORDER BY i.id DESC LIMIT 5")).mappings().all()
    )
    return {
        "acoes_ultima_semana": int(semana),
        # Estimativa fixa de economia por interação (MVP; sem telemetria real).
        "economia_tempo_min": 12,
        "taxa_sucesso": (int(ok) / int(total)) if total else 1.0,
        "ultimas_acoes": [dict(r) for r in ultimas_rows],
    }


# ── Copilot (F10.4) ───────────────────────────────────────────────────────
_COPILOT_BASE: dict[str, list[dict[str, str]]] = {
    "alvenaria": [
        {"descricao": "Bloco cerâmico 9x19x39", "unidade": "un", "quantidade": "1200"},
        {"descricao": "Argamassa de assentamento", "unidade": "kg", "quantidade": "480"},
        {"descricao": "Pedreiro (mão de obra)", "unidade": "h", "quantidade": "64"},
    ],
    "piso": [
        {"descricao": "Porcelanato 60x60", "unidade": "m²", "quantidade": "85"},
        {"descricao": "Argamassa colante AC-III", "unidade": "kg", "quantidade": "340"},
        {"descricao": "Rejunte flexível", "unidade": "kg", "quantidade": "25"},
    ],
    "pintura": [
        {"descricao": "Tinta acrílica premium", "unidade": "L", "quantidade": "72"},
        {"descricao": "Massa corrida PVA", "unidade": "kg", "quantidade": "120"},
        {"descricao": "Pintor (mão de obra)", "unidade": "h", "quantidade": "48"},
    ],
}


def copilot_suggest(descricao: str) -> list[dict[str, str]]:
    """Sugestão determinística de insumos (MVP sem LLM real — mesmo contrato do
    mock do frontend). Palavra-chave → composição; senão, genérico."""
    q = descricao.lower()
    for chave, itens in _COPILOT_BASE.items():
        if chave in q:
            return itens
    return [
        {"descricao": f"Material principal — {descricao}", "unidade": "un", "quantidade": "100"},
        {"descricao": "Mão de obra associada", "unidade": "h", "quantidade": "40"},
    ]
