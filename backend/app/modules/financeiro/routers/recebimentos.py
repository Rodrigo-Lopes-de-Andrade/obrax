"""Recebimentos (ESPEC §6.2). Stubs 501."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path, Query

from app.modules.financeiro.routers._common import (
    GERENCIA,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    RecebimentoOut,
    RecebimentoPage,
    RecebimentoReceber,
)
from app.modules.financeiro.schemas._types import RecebimentoStatus

router = APIRouter(tags=["financeiro-recebimentos"])

IdPath = Path(alias="id")


@router.get(
    "/financeiro/recebimentos",
    response_model=RecebimentoPage,
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Lista recebimentos, filtro por obra e status",
)
def list_recebimentos(
    obra_id: UUID | None = Query(default=None),
    status_: RecebimentoStatus | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> RecebimentoPage:
    nao_implementado()


@router.post(
    "/financeiro/recebimentos/{id}/receber",
    response_model=RecebimentoOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Marca o título como recebido",
)
def receber(payload: RecebimentoReceber, id_: UUID = IdPath) -> RecebimentoOut:
    nao_implementado()
