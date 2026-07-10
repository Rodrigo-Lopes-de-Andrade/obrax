"""Schemas dos relatórios gerenciais (B6.5, US-10).

Valores financeiros são `Decimal` (NUMERIC no banco) — float é proibido em
dinheiro (docs/CLAUDE.md). Cada relatório traz o breakdown por status
*zero-preenchido* na ordem canônica do enum, para o frontend renderizar tabela
e gráfico sem precisar conhecer os status ausentes.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ObrasStatusLinha(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    count: int
    valor: Decimal  # soma de valor_contrato das obras neste status


class RelatorioObrasAtivas(BaseModel):
    """Obras por status (US-10). `ativas`/`valor_ativas` somam as não concluídas
    nem canceladas — o mesmo recorte do KPI do dashboard."""

    model_config = ConfigDict(extra="forbid")

    ativas: int
    valor_ativas: Decimal
    total: int
    por_status: list[ObrasStatusLinha]


class OrcamentosStatusLinha(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    count: int
    preco_venda: Decimal  # soma do preço de venda das versões atuais neste status


class RelatorioOrcamentos(BaseModel):
    """Orçamentos por status (US-10), agregando o preço de venda da versão atual
    de cada orçamento. `pendentes` = aguardando aprovação (espelha o dashboard)."""

    model_config = ConfigDict(extra="forbid")

    total: int
    preco_venda_total: Decimal
    pendentes: int
    por_status: list[OrcamentosStatusLinha]
