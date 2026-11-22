"""Análise (ESPEC §6.3). Stubs 501."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.financeiro.routers._common import (
    ANALISE,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    CurvaSOut,
    FluxoCaixaOut,
    OrcadoRealizadoOut,
)
from app.modules.financeiro.schemas._types import Periodicidade

router = APIRouter(tags=["financeiro-analise"])


@router.get(
    "/obras/{obra_id}/financeiro/orcado-realizado",
    response_model=OrcadoRealizadoOut,
    dependencies=[ANALISE],
    responses=RESP_501,
    summary="Orçado x realizado por fase, com comprometido e alerta",
)
def orcado_realizado(obra_id: UUID) -> OrcadoRealizadoOut:
    nao_implementado()


@router.get(
    "/obras/{obra_id}/financeiro/curva-s",
    response_model=CurvaSOut,
    dependencies=[ANALISE],
    responses=RESP_501,
    summary="Três séries acumuladas por período",
)
def curva_s(obra_id: UUID) -> CurvaSOut:
    nao_implementado()


@router.get(
    "/financeiro/fluxo-caixa",
    response_model=FluxoCaixaOut,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Previsto x realizado por período",
)
def fluxo_caixa(
    de: date,
    ate: date,
    obra_id: UUID | None = Query(default=None),
    periodicidade: Periodicidade = Query(default="mensal"),
) -> FluxoCaixaOut:
    nao_implementado()
