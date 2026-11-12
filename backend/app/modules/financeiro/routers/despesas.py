"""Despesas e export CSV (ESPEC §6.2, §6.4). Stubs 501."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Path, Query, status
from fastapi.responses import Response

from app.modules.financeiro.routers._common import (
    DESPESA_ESCRITA,
    GERENCIA,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    DespesaCreate,
    DespesaOut,
    DespesaPagar,
    DespesaPage,
    DespesaParceladaCreate,
    DespesaParceladaOut,
    DespesaUpdate,
)
from app.modules.financeiro.schemas._types import DespesaStatus

router = APIRouter(tags=["financeiro-despesas"])

IdPath = Path(alias="id")


@router.get(
    "/obras/{obra_id}/despesas",
    response_model=DespesaPage,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Lista despesas da obra",
)
def list_despesas(
    obra_id: UUID,
    status_: DespesaStatus | None = Query(default=None, alias="status"),
    obra_fase_id: UUID | None = Query(default=None),
    categoria_id: UUID | None = Query(default=None),
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> DespesaPage:
    nao_implementado()


@router.post(
    "/obras/{obra_id}/despesas",
    response_model=DespesaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[DESPESA_ESCRITA],
    responses=RESP_501,
    summary="Lança despesa",
)
def create_despesa(obra_id: UUID, payload: DespesaCreate) -> DespesaOut:
    nao_implementado()


@router.post(
    "/obras/{obra_id}/despesas/parcelada",
    response_model=DespesaParceladaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[DESPESA_ESCRITA],
    responses=RESP_501,
    summary="Gera N títulos numa transação",
)
def create_despesa_parcelada(obra_id: UUID, payload: DespesaParceladaCreate) -> DespesaParceladaOut:
    nao_implementado()


@router.get(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Detalhe da despesa",
)
def get_despesa(id_: UUID = IdPath) -> DespesaOut:
    nao_implementado()


@router.patch(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[DESPESA_ESCRITA],
    responses=RESP_501,
    summary="Edita despesa",
)
def update_despesa(payload: DespesaUpdate, id_: UUID = IdPath) -> DespesaOut:
    nao_implementado()


@router.delete(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Cancela a despesa (devolve a despesa com status cancelada)",
)
def delete_despesa(id_: UUID = IdPath) -> DespesaOut:
    nao_implementado()


@router.post(
    "/financeiro/despesas/{id}/pagar",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Registra pagamento",
)
def pagar_despesa(payload: DespesaPagar, id_: UUID = IdPath) -> DespesaOut:
    nao_implementado()


@router.post(
    "/financeiro/despesas/{id}/estornar",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Desfaz o pagamento (volta a prevista)",
)
def estornar_despesa(id_: UUID = IdPath) -> DespesaOut:
    nao_implementado()


@router.get(
    "/obras/{obra_id}/financeiro/export.csv",
    response_class=Response,
    dependencies=[LEITURA],
    responses={
        **RESP_501,
        200: {
            "description": "CSV (teto de 10.000 linhas; acima, 422).",
            "content": {"text/csv": {}},
        },
    },
    summary="Exporta lançamentos em CSV",
)
def export_csv(
    obra_id: UUID,
    status_: DespesaStatus | None = Query(default=None, alias="status"),
    obra_fase_id: UUID | None = Query(default=None),
    categoria_id: UUID | None = Query(default=None),
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
) -> Response:
    nao_implementado()
