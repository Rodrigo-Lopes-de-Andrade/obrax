"""Router de equipes — membros de uma obra (B3.6, US-07).

Montado sem prefixo (paths absolutos aninhados na obra: `/obras/{id}/membros`),
conforme docs/ESPEC.md § 6. Leitura: qualquer usuário do tenant. Escrita
(add/remove): `owner`/`admin`/`gestor`. Isolamento por empresa via RLS no
`get_db`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.modules.gestao.equipes import service
from app.modules.gestao.equipes.schemas import (
    MembroCreate,
    MembroOut,
    MembroPage,
    UsuarioOut,
    UsuarioPage,
)

router = APIRouter(tags=["equipes"])

_WRITE_ROLES = require_roles("owner", "admin", "gestor")


@router.post(
    "/obras/{obra_id}/membros",
    response_model=MembroOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_WRITE_ROLES)],
)
def add_membro(
    obra_id: UUID,
    payload: MembroCreate,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> MembroOut:
    row = service.add_membro(session, company_id=company_id, obra_id=obra_id, payload=payload)
    return MembroOut.model_validate(row)


@router.get("/obras/{obra_id}/membros", response_model=MembroPage)
def list_membros(
    obra_id: UUID,
    session: Session = Depends(get_db),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> MembroPage:
    items, next_cursor = service.list_membros(session, obra_id=obra_id, cursor=cursor, limit=limit)
    return MembroPage(
        items=[MembroOut.model_validate(row) for row in items], next_cursor=next_cursor
    )


@router.delete(
    "/obras/{obra_id}/membros/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(_WRITE_ROLES)],
)
def remove_membro(obra_id: UUID, user_id: UUID, session: Session = Depends(get_db)) -> None:
    service.remove_membro(session, obra_id=obra_id, user_id=user_id)


@router.get("/usuarios", response_model=UsuarioPage)
def search_usuarios(
    session: Session = Depends(get_db),
    search: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=100),
) -> UsuarioPage:
    """Usuários do tenant para o seletor de "adicionar membro"/menções (US-07).
    Leitura aberta a qualquer usuário autenticado do tenant."""
    rows = service.search_usuarios(session, search=search, limit=limit)
    # Lista curta e filtrada no cliente (o seletor busca por texto): sem paginação
    # por cursor — `next_cursor` existe só para manter a forma de `Page<T>` do front.
    return UsuarioPage(items=[UsuarioOut.model_validate(r) for r in rows], next_cursor=None)
