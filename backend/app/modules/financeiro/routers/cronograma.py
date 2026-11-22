"""Cronograma (ESPEC §6.1). Stubs 501."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path, status

from app.modules.financeiro.routers._common import (
    GERENCIA,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    AlocacoesPut,
    CronogramaCreate,
    CronogramaGradeOut,
)

router = APIRouter(tags=["financeiro-cronograma"])

IdPath = Path(alias="id")


@router.post(
    "/obras/{obra_id}/cronograma",
    response_model=CronogramaGradeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Cria o cronograma a partir da versão aprovada",
)
def create_cronograma(obra_id: UUID, payload: CronogramaCreate) -> CronogramaGradeOut:
    nao_implementado()


@router.get(
    "/obras/{obra_id}/cronograma",
    response_model=CronogramaGradeOut,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Grade fase x período",
)
def get_cronograma(obra_id: UUID) -> CronogramaGradeOut:
    nao_implementado()


@router.put(
    "/cronograma/{id}/alocacoes",
    response_model=CronogramaGradeOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Ajusta a distribuição (bulk, substitui o conjunto)",
)
def put_alocacoes(payload: AlocacoesPut, id_: UUID = IdPath) -> CronogramaGradeOut:
    nao_implementado()
