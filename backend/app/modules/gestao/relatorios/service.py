"""Agregações dos relatórios gerenciais (B6.5, US-10).

Roda via `get_db` (role `app_user`, RLS ativa): cada agregação enxerga só as
linhas do tenant — nenhum filtro `company_id` na mão. Usa os índices
`(company_id, status)` de obras/orçamento, mantendo o custo baixo (< 100ms);
o cache de 5min (router) é folga, não necessidade.

O breakdown por status é *zero-preenchido* na ordem canônica do enum, para o
relatório ser estável (todo status sempre presente) mesmo sem linhas.
**Proibido float** — somas em `Decimal` (NUMERIC no banco).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gestao.relatorios.schemas import (
    ObrasStatusLinha,
    OrcamentosStatusLinha,
    RelatorioObrasAtivas,
    RelatorioOrcamentos,
)

# Ordem canônica dos enums (mesma dos migrations 0003/0009/0019) — dá estabilidade
# ao relatório e casa com a ordem que o frontend renderiza.
_OBRA_STATUS = ("planejamento", "execucao", "pausada", "concluida", "cancelada")
_OBRA_INATIVAS = frozenset({"concluida", "cancelada"})
_ORCAMENTO_STATUS = ("rascunho", "em_revisao", "aguardando_aprovacao", "aprovado", "rejeitado")

_OBRAS_SQL = text(
    "SELECT status, count(*) AS count, coalesce(sum(valor_contrato), 0) AS valor "
    "FROM obras WHERE deleted_at IS NULL GROUP BY status"
)
_ORCAMENTOS_SQL = text(
    "SELECT o.status, count(*) AS count, coalesce(sum(v.preco_venda), 0) AS preco_venda "
    "FROM orcamento o "
    "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
    "WHERE o.deleted_at IS NULL GROUP BY o.status"
)


def obras_ativas(session: Session) -> RelatorioObrasAtivas:
    rows = {r["status"]: r for r in session.execute(_OBRAS_SQL).mappings().all()}
    por_status = [
        ObrasStatusLinha(
            status=st,
            count=rows[st]["count"] if st in rows else 0,
            valor=rows[st]["valor"] if st in rows else Decimal("0.00"),
        )
        for st in _OBRA_STATUS
    ]
    ativas = [ln for ln in por_status if ln.status not in _OBRA_INATIVAS]
    return RelatorioObrasAtivas(
        ativas=sum(ln.count for ln in ativas),
        valor_ativas=sum((ln.valor for ln in ativas), Decimal("0.00")),
        total=sum(ln.count for ln in por_status),
        por_status=por_status,
    )


def orcamentos(session: Session) -> RelatorioOrcamentos:
    rows: dict[str, Any] = {
        r["status"]: r for r in session.execute(_ORCAMENTOS_SQL).mappings().all()
    }
    por_status = [
        OrcamentosStatusLinha(
            status=st,
            count=rows[st]["count"] if st in rows else 0,
            preco_venda=rows[st]["preco_venda"] if st in rows else Decimal("0.00"),
        )
        for st in _ORCAMENTO_STATUS
    ]
    pendentes = next((ln.count for ln in por_status if ln.status == "aguardando_aprovacao"), 0)
    return RelatorioOrcamentos(
        total=sum(ln.count for ln in por_status),
        preco_venda_total=sum((ln.preco_venda for ln in por_status), Decimal("0.00")),
        pendentes=pendentes,
        por_status=por_status,
    )
