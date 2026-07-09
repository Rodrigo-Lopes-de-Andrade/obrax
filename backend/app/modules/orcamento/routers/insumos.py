"""Router do catálogo de insumos (B5.6, US-05) — autocomplete servidor-side.

Somente leitura, aberto a qualquer usuário do tenant (a RLS expõe o catálogo
SINAPI global + os insumos do próprio tenant). Prefixo `/insumos`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.orcamento.schemas import InsumoCategorias, InsumoOut, InsumoPage
from app.modules.orcamento.services import insumos as service

router = APIRouter(tags=["insumos"])


@router.get("/insumos", response_model=InsumoPage)
def search_insumos(
    session: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=120),
    categoria: str | None = Query(default=None, max_length=120),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> InsumoPage:
    items, next_cursor = service.search_insumos(
        session, search=search, categoria=categoria, cursor=cursor, limit=limit
    )
    return InsumoPage(
        items=[InsumoOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.get("/insumos/categorias", response_model=InsumoCategorias)
def list_categorias(session: Session = Depends(get_db)) -> InsumoCategorias:
    return InsumoCategorias(categorias=service.list_categorias(session))
