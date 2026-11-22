"""Despesas (ESPEC §6.2, US-F06/F08/F09). O export CSV segue stub 501 (S-F14)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_tenant
from app.core.middleware import AuthContext

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
    FaseObraOut,
)
from app.modules.financeiro.schemas._types import DespesaStatus
from app.modules.financeiro.services import despesas as service

router = APIRouter(tags=["financeiro-despesas"])

IdPath = Path(alias="id")


@router.get(
    "/obras/{obra_id}/fases",
    response_model=list[FaseObraOut],
    dependencies=[DESPESA_ESCRITA],
    summary="Fases da obra (seletor de lançamento)",
)
def list_fases(obra_id: UUID, session: Session = Depends(get_db)) -> list[FaseObraOut]:
    return [FaseObraOut.model_validate(r) for r in service.listar_fases(session, obra_id)]


@router.get(
    "/obras/{obra_id}/despesas",
    response_model=DespesaPage,
    dependencies=[LEITURA],
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
    session: Session = Depends(get_db),
) -> DespesaPage:
    rows, next_cursor = service.listar_despesas(
        session,
        obra_id=obra_id,
        status_filter=status_,
        obra_fase_id=obra_fase_id,
        categoria_id=categoria_id,
        de=de,
        ate=ate,
        cursor=cursor,
        limit=limit,
    )
    return DespesaPage(items=[DespesaOut.model_validate(r) for r in rows], next_cursor=next_cursor)


@router.post(
    "/obras/{obra_id}/despesas",
    response_model=DespesaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[DESPESA_ESCRITA],
    summary="Lança despesa",
)
def create_despesa(
    obra_id: UUID,
    payload: DespesaCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DespesaOut:
    row = service.criar_despesa(
        session, company_id=company_id, user_id=str(auth.user_id), obra_id=obra_id, payload=payload
    )
    return DespesaOut.model_validate(row)


@router.post(
    "/obras/{obra_id}/despesas/parcelada",
    response_model=DespesaParceladaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[DESPESA_ESCRITA],
    summary="Gera N títulos numa transação",
)
def create_despesa_parcelada(
    obra_id: UUID,
    payload: DespesaParceladaCreate,
    company_id: str = Depends(get_tenant),
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DespesaParceladaOut:
    grupo, rows = service.criar_despesa_parcelada(
        session, company_id=company_id, user_id=str(auth.user_id), obra_id=obra_id, payload=payload
    )
    return DespesaParceladaOut(
        grupo_parcelas_id=grupo, parcelas=[DespesaOut.model_validate(r) for r in rows]
    )


@router.get(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[LEITURA],
    summary="Detalhe da despesa",
)
def get_despesa(id_: UUID = IdPath, session: Session = Depends(get_db)) -> DespesaOut:
    return DespesaOut.model_validate(service.obter_despesa(session, id_))


@router.patch(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[DESPESA_ESCRITA],
    summary="Edita despesa",
)
def update_despesa(
    payload: DespesaUpdate,
    id_: UUID = IdPath,
    session: Session = Depends(get_db),
) -> DespesaOut:
    row = service.atualizar_despesa(session, despesa_id=id_, payload=payload)
    return DespesaOut.model_validate(row)


@router.delete(
    "/financeiro/despesas/{id}",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    summary="Cancela a despesa (devolve a despesa com status cancelada)",
)
def delete_despesa(
    id_: UUID = IdPath,
    session: Session = Depends(get_db),
) -> DespesaOut:
    row = service.cancelar_despesa(session, despesa_id=id_)
    return DespesaOut.model_validate(row)


@router.post(
    "/financeiro/despesas/{id}/pagar",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    summary="Registra pagamento",
)
def pagar_despesa(
    payload: DespesaPagar,
    id_: UUID = IdPath,
    session: Session = Depends(get_db),
) -> DespesaOut:
    row = service.pagar_despesa(session, despesa_id=id_, data_pagamento=payload.data_pagamento)
    return DespesaOut.model_validate(row)


@router.post(
    "/financeiro/despesas/{id}/estornar",
    response_model=DespesaOut,
    dependencies=[GERENCIA],
    summary="Desfaz o pagamento (volta a prevista)",
)
def estornar_despesa(
    id_: UUID = IdPath,
    session: Session = Depends(get_db),
) -> DespesaOut:
    row = service.estornar_despesa(session, despesa_id=id_)
    return DespesaOut.model_validate(row)


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
