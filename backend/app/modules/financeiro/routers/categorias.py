"""Categorias do financeiro (ESPEC §6.2, US-F05)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant

from app.modules.financeiro.routers._common import (
    GERENCIA,
    LEITURA,
)
from app.modules.financeiro.schemas import (
    CategoriaCreate,
    CategoriaOut,
    CategoriaUpdate,
)
from app.modules.financeiro.services import despesas as service

router = APIRouter(tags=["financeiro-categorias"])

IdPath = Path(alias="id")


@router.get(
    "/financeiro/categorias",
    response_model=list[CategoriaOut],
    dependencies=[LEITURA],
    summary="Plano de contas da empresa",
)
def list_categorias(
    incluir_inativas: bool = Query(default=False),
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> list[CategoriaOut]:
    rows = service.listar_categorias(
        session, company_id=company_id, incluir_inativas=incluir_inativas
    )
    return [CategoriaOut.model_validate(r) for r in rows]


@router.post(
    "/financeiro/categorias",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GERENCIA],
    summary="Cria categoria",
)
def create_categoria(
    payload: CategoriaCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> CategoriaOut:
    row = service.criar_categoria(session, company_id=company_id, payload=payload)
    return CategoriaOut.model_validate(row)


@router.patch(
    "/financeiro/categorias/{id}",
    response_model=CategoriaOut,
    dependencies=[GERENCIA],
    summary="Renomear, ativar ou desativar",
)
def update_categoria(
    payload: CategoriaUpdate,
    id_: UUID = IdPath,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> CategoriaOut:
    row = service.atualizar_categoria(
        session, company_id=company_id, categoria_id=id_, payload=payload
    )
    return CategoriaOut.model_validate(row)
