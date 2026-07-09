"""B5.6 — busca no catálogo de insumos (autocomplete servidor-side).

Roda sob `get_db` (RLS): a policy `insumo_read` já expõe o catálogo SINAPI
global (company_id NULL) + os insumos do próprio tenant. Busca por descrição
(ou código) via ILIKE — apoiada no índice GIN trigram. Paginação keyset por
(descricao, id) para ordenação estável no autocomplete.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

_COLUMNS = (
    "id, codigo, descricao, unidade, categoria, preco_unitario, "
    "(company_id IS NOT NULL) AS is_custom"
)


def search_insumos(
    session: Session,
    *,
    search: str | None,
    categoria: str | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    if cursor is not None:
        try:
            uuid.UUID(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cursor inválido"
            ) from exc

    termo = search.strip() if search else None
    rows = (
        session.execute(
            text(
                f"SELECT {_COLUMNS} FROM insumo "
                "WHERE (CAST(:termo AS text) IS NULL "
                "       OR descricao ILIKE '%' || :termo || '%' "
                "       OR codigo ILIKE '%' || :termo || '%') "
                "  AND (CAST(:categoria AS text) IS NULL OR categoria = :categoria) "
                "  AND (CAST(:cursor AS uuid) IS NULL OR (descricao, id) > ("
                "        (SELECT descricao FROM insumo WHERE id = CAST(:cursor AS uuid)), "
                "        CAST(:cursor AS uuid))) "
                "ORDER BY descricao ASC, id ASC "
                "LIMIT :limit_plus_one"
            ),
            {
                "termo": termo,
                "categoria": categoria,
                "cursor": cursor,
                "limit_plus_one": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def list_categorias(session: Session) -> list[str]:
    rows = session.execute(
        text("SELECT DISTINCT categoria FROM insumo WHERE categoria IS NOT NULL ORDER BY categoria")
    ).scalars()
    return list(rows)
