"""Medições (ESPEC §6.1). Stubs 501."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from app.modules.financeiro.routers._common import (
    APROVAR,
    GERENCIA,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    MedicaoAprovadaOut,
    MedicaoAprovar,
    MedicaoCreate,
    MedicaoDetail,
    MedicaoItensPut,
    MedicaoPage,
)

router = APIRouter(tags=["financeiro-medicao"])

IdPath = Path(alias="id")


@router.get(
    "/obras/{obra_id}/medicoes",
    response_model=MedicaoPage,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Lista medições da obra",
)
def list_medicoes(
    obra_id: UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> MedicaoPage:
    nao_implementado()


@router.post(
    "/obras/{obra_id}/medicoes",
    response_model=MedicaoDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Cria rascunho de medição para um período",
)
def create_medicao(obra_id: UUID, payload: MedicaoCreate) -> MedicaoDetail:
    nao_implementado()


@router.get(
    "/medicoes/{id}",
    response_model=MedicaoDetail,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Detalhe da medição com itens",
)
def get_medicao(id_: UUID = IdPath) -> MedicaoDetail:
    nao_implementado()


@router.put(
    "/medicoes/{id}/itens",
    response_model=MedicaoDetail,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Grava os percentuais acumulados (bulk)",
)
def put_medicao_itens(payload: MedicaoItensPut, id_: UUID = IdPath) -> MedicaoDetail:
    nao_implementado()


@router.post(
    "/medicoes/{id}/aprovar",
    response_model=MedicaoAprovadaOut,
    dependencies=[APROVAR],
    responses=RESP_501,
    summary="Imutabiliza a medição e gera o recebimento",
)
def aprovar_medicao(payload: MedicaoAprovar, id_: UUID = IdPath) -> MedicaoAprovadaOut:
    nao_implementado()
