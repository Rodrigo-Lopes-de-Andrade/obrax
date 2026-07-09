"""B5.3 — regras de negócio do CRUD de orçamento (US-11).

Roda sob `get_db` (role `app_user`, RLS ativa) — nenhuma query filtra
`company_id` na mão. Criar um orçamento cria, na mesma transação, a versão 1
(vazia); o ponteiro `versao_atual` liga o orçamento à revisão corrente.

Transição de status é uma máquina de estados explícita; aprovar trava
(`is_locked`) a versão atual — a partir daí ela é um snapshot imutável (o
trigger de banco de B5.1 é o backstop).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.orcamento.schemas import OrcamentoCreate

_ORC_COLUMNS = "id, obra_id, titulo, status, versao_atual, created_at"
_VERSAO_COLUMNS = (
    "id, numero, is_locked, custo_direto, markup_global, taxa_adm, preco_venda, margem, created_at"
)

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="orçamento não encontrado")
_OBRA_INVALIDA = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="obra não encontrada"
)

# Máquina de estados do orçamento (docs/ESPEC.md § 7). `aprovado` é terminal.
_TRANSICOES: dict[str, set[str]] = {
    "rascunho": {"em_revisao", "aguardando_aprovacao"},
    "em_revisao": {"rascunho", "aguardando_aprovacao"},
    "aguardando_aprovacao": {"aprovado", "rejeitado", "em_revisao"},
    "rejeitado": {"rascunho", "em_revisao"},
    "aprovado": set(),
}


def _assert_obra_do_tenant(session: Session, obra_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"),
        {"id": obra_id},
    ).first()
    if row is None:
        raise _OBRA_INVALIDA


def _detail(session: Session, orcamento_id: uuid.UUID) -> dict[str, Any]:
    """Orçamento + a versão atual (join por numero = versao_atual)."""
    row = (
        session.execute(
            text(
                "SELECT "
                + ", ".join(f"o.{c}" for c in _ORC_COLUMNS.split(", "))
                + ", "
                + ", ".join(f"v.{c} AS versao_{c}" for c in _VERSAO_COLUMNS.split(", "))
                + " FROM orcamento o "
                "JOIN orcamento_versao v "
                "  ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
                "WHERE o.id = :id AND o.deleted_at IS NULL"
            ),
            {"id": orcamento_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NOT_FOUND
    return {
        "id": row["id"],
        "obra_id": row["obra_id"],
        "titulo": row["titulo"],
        "status": row["status"],
        "versao_atual": row["versao_atual"],
        "created_at": row["created_at"],
        "versao": {c: row[f"versao_{c}"] for c in _VERSAO_COLUMNS.split(", ")},
    }


def create_orcamento(
    session: Session,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: OrcamentoCreate,
) -> dict[str, Any]:
    _assert_obra_do_tenant(session, obra_id)
    orcamento_id = session.execute(
        text(
            "INSERT INTO orcamento (company_id, obra_id, titulo, created_by) "
            "VALUES (:cid, :obra_id, :titulo, :created_by) RETURNING id"
        ),
        {
            "cid": company_id,
            "obra_id": obra_id,
            "titulo": payload.titulo,
            "created_by": created_by,
        },
    ).scalar_one()
    session.execute(
        text(
            "INSERT INTO orcamento_versao (company_id, orcamento_id, numero, criado_por) "
            "VALUES (:cid, :orc, 1, :criado_por)"
        ),
        {"cid": company_id, "orc": orcamento_id, "criado_por": created_by},
    )
    return _detail(session, orcamento_id)


def list_orcamentos(
    session: Session,
    *,
    obra_id: uuid.UUID | None,
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

    rows = (
        session.execute(
            text(
                f"SELECT {_ORC_COLUMNS} FROM orcamento "
                "WHERE deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:obra_id AS uuid) IS NULL OR obra_id = CAST(:obra_id AS uuid)) "
                "ORDER BY id DESC LIMIT :limit_plus_one"
            ),
            {"cursor": cursor, "obra_id": obra_id, "limit_plus_one": limit + 1},
        )
        .mappings()
        .all()
    )
    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    next_cursor = str(page[-1]["id"]) if has_more else None
    return page, next_cursor


def get_orcamento(session: Session, orcamento_id: uuid.UUID) -> dict[str, Any]:
    return _detail(session, orcamento_id)


def update_status(session: Session, *, orcamento_id: uuid.UUID, new_status: str) -> dict[str, Any]:
    atual = (
        session.execute(
            text(
                "SELECT status, versao_atual FROM orcamento "
                "WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": orcamento_id},
        )
        .mappings()
        .first()
    )
    if atual is None:
        raise _NOT_FOUND

    current: str = atual["status"]
    if new_status != current and new_status not in _TRANSICOES.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"transição inválida: {current} → {new_status}",
        )

    session.execute(
        text("UPDATE orcamento SET status = CAST(:s AS orcamento_status) WHERE id = :id"),
        {"s": new_status, "id": orcamento_id},
    )
    # Aprovar congela a versão atual: snapshot imutável (não editável, não recalc).
    if new_status == "aprovado":
        session.execute(
            text(
                "UPDATE orcamento_versao SET is_locked = true "
                "WHERE orcamento_id = :orc AND numero = :n"
            ),
            {"orc": orcamento_id, "n": atual["versao_atual"]},
        )
    return _detail(session, orcamento_id)


def soft_delete_orcamento(session: Session, orcamento_id: uuid.UUID) -> None:
    row = session.execute(
        text(
            "UPDATE orcamento SET deleted_at = now() "
            "WHERE id = :id AND deleted_at IS NULL RETURNING id"
        ),
        {"id": orcamento_id},
    ).first()
    if row is None:
        raise _NOT_FOUND
