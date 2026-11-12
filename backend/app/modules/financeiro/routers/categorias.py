"""Categorias do financeiro (ESPEC §6.2). Stubs 501."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from app.modules.financeiro.routers._common import (
    GERENCIA,
    LEITURA,
    RESP_501,
    nao_implementado,
)
from app.modules.financeiro.schemas import (
    CategoriaCreate,
    CategoriaOut,
    CategoriaUpdate,
)

router = APIRouter(tags=["financeiro-categorias"])

IdPath = Path(alias="id")


@router.get(
    "/financeiro/categorias",
    response_model=list[CategoriaOut],
    dependencies=[LEITURA],
    responses=RESP_501,
    summary="Plano de contas da empresa",
)
def list_categorias(incluir_inativas: bool = Query(default=False)) -> list[CategoriaOut]:
    nao_implementado()


@router.post(
    "/financeiro/categorias",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Cria categoria",
)
def create_categoria(payload: CategoriaCreate) -> CategoriaOut:
    nao_implementado()


@router.patch(
    "/financeiro/categorias/{id}",
    response_model=CategoriaOut,
    dependencies=[GERENCIA],
    responses=RESP_501,
    summary="Renomear, ativar ou desativar",
)
def update_categoria(payload: CategoriaUpdate, id_: UUID = IdPath) -> CategoriaOut:
    nao_implementado()
