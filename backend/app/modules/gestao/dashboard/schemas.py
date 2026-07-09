"""Schemas do dashboard admin (B4.4, US-01) — KPIs agregados por tenant.

`obras_valor_total` é `Decimal` (NUMERIC no banco) — float é proibido em
valores financeiros (docs/CLAUDE.md > Precisão financeira), igual ao contrato
de obras.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Obras "ativas" = não concluídas nem canceladas (ver service).
    obras_ativas: int
    obras_valor_total: Decimal
    tickets_abertos: int
    # Placeholder até a Sprint 5 (tabela `orcamento` só existe a partir de B5.1).
    orcamentos_pendentes: int
