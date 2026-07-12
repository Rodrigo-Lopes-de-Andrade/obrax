"""Subagentes do orquestrador (B10.4 Orçamento, B10.5 Compras).

Cada subagente expõe "tools" (consultas/ações sobre o domínio, escopadas ao
tenant pela RLS da sessão) e devolve um `SubagentResult` que o responder entrega
ao usuário e o auditor grava em `agent_interaction`.

- Orçamento (B10.4): **read-only** — status da obra e resumo do orçamento
  (preço de venda, sem custo/markup, coerente com o portal do cliente).
- Compras (B10.5): **write** — registra a solicitação de compra. O Módulo 4
  (Compras) não tem tabela no MVP V1 (docs/CLAUDE.md: não criar telas/rotas),
  então a própria linha de `agent_interaction` é o registro da solicitação; a
  reversão (US-22) marca essa linha como revertida. A ação exige papel
  `solicitador`/`aprovador` e respeita o limite de gasto (checados no
  orquestrador antes de chamar o subagente).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_CODIGO_RE = re.compile(r"\bOBR-\d+\b", re.IGNORECASE)


@dataclass(frozen=True)
class SubagentResult:
    """Resposta de um subagente. `action` é preenchido só quando houve efeito
    (write); consultas deixam `action=None` (não são reversíveis)."""

    agent: str
    reply: str
    action: str | None
    obra_id: UUID | None


def _brl(value: Decimal) -> str:
    # R$ 1.234,56 — formatação simples pt-BR sem depender de locale.
    inteiro, _, cents = f"{value:.2f}".partition(".")
    milhar = re.sub(r"(?<=\d)(?=(\d{3})+$)", ".", inteiro)
    return f"R$ {milhar},{cents}"


def resolve_obra(session: Session, message: str) -> tuple[UUID, str] | None:
    """Resolve a obra-alvo: por código citado (OBR-####), senão a mais recente
    do tenant. Retorna (id, codigo) ou None se o tenant não tem obras."""
    match = _CODIGO_RE.search(message)
    if match:
        row = (
            session.execute(
                text(
                    "SELECT id, codigo FROM obras "
                    "WHERE deleted_at IS NULL AND upper(codigo) = upper(:c) LIMIT 1"
                ),
                {"c": match.group(0)},
            )
            .mappings()
            .first()
        )
        if row is not None:
            return row["id"], row["codigo"]
    row = (
        session.execute(
            text("SELECT id, codigo FROM obras WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 1")
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return row["id"], row["codigo"]


def _status_obra(session: Session, obra_id: UUID) -> str:
    row = (
        session.execute(
            text("SELECT codigo, nome, status FROM obras WHERE id = :id"), {"id": obra_id}
        )
        .mappings()
        .one()
    )
    return f"A obra {row['codigo']} ({row['nome']}) está em {row['status']}."


def _orcamento_resumo(session: Session, obra_id: UUID) -> str:
    row = (
        session.execute(
            text(
                "SELECT v.preco_venda "
                "FROM orcamento o "
                "JOIN orcamento_versao v "
                "  ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
                "WHERE o.obra_id = :obra AND o.deleted_at IS NULL "
                "ORDER BY o.created_at DESC LIMIT 1"
            ),
            {"obra": obra_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return "Ainda não há orçamento cadastrado para esta obra."
    return f"O orçamento vigente soma {_brl(Decimal(row['preco_venda']))} de preço de venda."


def orcamento_subagent(session: Session, *, message: str, intent: str) -> SubagentResult:
    """Read-only: status ou resumo de orçamento da obra-alvo."""
    resolved = resolve_obra(session, message)
    if resolved is None:
        return SubagentResult(
            agent="orcamento",
            reply="Não encontrei nenhuma obra cadastrada para consultar.",
            action=None,
            obra_id=None,
        )
    obra_id, _codigo = resolved
    if intent == "consulta_orcamento":
        reply = _orcamento_resumo(session, obra_id)
    else:
        reply = _status_obra(session, obra_id)
    return SubagentResult(agent="orcamento", reply=reply, action=None, obra_id=obra_id)


def compras_subagent(session: Session, *, message: str) -> SubagentResult:
    """Write: registra a solicitação de compra (a linha de auditoria é o
    registro; ver docstring do módulo). Permissão/limite checados no orquestrador."""
    resolved = resolve_obra(session, message)
    obra_id = resolved[0] if resolved else None
    codigo = resolved[1] if resolved else "sem obra"
    reply = f"Solicitação de compra registrada para {codigo}. A equipe de compras foi notificada."
    return SubagentResult(
        agent="compras",
        reply=reply,
        action="criar_solicitacao_compra",
        obra_id=obra_id,
    )
