"""Agregações do dashboard admin (B4.4, US-01).

Roda via `get_db` (role `app_user`, RLS ativa): cada subquery enxerga só as
linhas do tenant corrente — nenhum filtro `company_id` na mão. As agregações
usam os índices `(company_id, status)` de obras e ticket (docs/ESPEC.md § 7),
o que mantém o custo baixo (< 100ms) mesmo sem cache.

Definições:
- obras ativas: `status NOT IN ('concluida','cancelada')` e não soft-deletadas.
  `valor_total` soma o `valor_contrato` dessas obras (NULL conta como 0).
- tickets abertos: `status = 'aberto'` e não soft-deletados.
- orçamentos pendentes: `status = 'aguardando_aprovacao'` e não soft-deletados —
  os que esperam decisão do gestor (B6.5 fecha o placeholder de B4.4).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gestao.dashboard.schemas import DashboardSummary

_SUMMARY_SQL = text(
    "SELECT "
    "  (SELECT count(*) FROM obras "
    "     WHERE deleted_at IS NULL AND status NOT IN ('concluida','cancelada')) "
    "    AS obras_ativas, "
    "  (SELECT coalesce(sum(valor_contrato), 0) FROM obras "
    "     WHERE deleted_at IS NULL AND status NOT IN ('concluida','cancelada')) "
    "    AS obras_valor_total, "
    "  (SELECT count(*) FROM ticket "
    "     WHERE deleted_at IS NULL AND status = 'aberto') "
    "    AS tickets_abertos, "
    "  (SELECT count(*) FROM orcamento "
    "     WHERE deleted_at IS NULL AND status = 'aguardando_aprovacao') "
    "    AS orcamentos_pendentes"
)


def compute_summary(session: Session) -> DashboardSummary:
    row = session.execute(_SUMMARY_SQL).mappings().one()
    return DashboardSummary(
        obras_ativas=row["obras_ativas"],
        obras_valor_total=row["obras_valor_total"],
        tickets_abertos=row["tickets_abertos"],
        orcamentos_pendentes=row["orcamentos_pendentes"],
    )
