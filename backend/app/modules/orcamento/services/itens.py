"""B5.4 — itens da EAP (US-12): bulk insert, PATCH, DELETE, reordenar (DnD) e
duplicar. Toda mutação dispara o recálculo (BudgetCalculator) e devolve a
árvore recalculada (a UI re-renderiza a partir da verdade do servidor).

Materialized path/depth são reindexados após mudanças estruturais (bulk,
reorder, duplicar) por uma varredura da árvore — barato e sem bugs de subárvore.
DELETE cascateia a subárvore (self-FK) e não altera o path dos demais.

Versão aprovada (`is_locked`) é imutável: 409 antes de qualquer escrita (o
trigger de banco é o backstop). Hierarquia válida: F(raiz) → S(sob F) → I(sob S).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Integer, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Session

from app.modules.orcamento.schemas import (
    EapTree,
    ItemCreate,
    ItemUpdate,
    ReorderItem,
)
from app.modules.orcamento.services import budget_calculator

_ITEM_COLUMNS = (
    "id, versao_id, parent_id, tipo, depth, path, sort_order, codigo, descricao, "
    "unidade, quantidade, preco_unitario, markup_override, custo_total, subtotal"
)

_VERSAO_NAO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="versão não encontrada"
)
_ITEM_NAO_ENCONTRADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="item não encontrado"
)
_VERSAO_TRAVADA = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="versão aprovada é imutável"
)

# tipo do pai exigido por tipo do filho (F é raiz).
_PARENT_TIPO: dict[str, str | None] = {"F": None, "S": "F", "I": "S"}

_REINDEX = text(
    "UPDATE orcamento_item AS oi SET path = d.path, depth = d.depth "
    "FROM unnest(:ids, :paths, :depths) AS d(id, path, depth) WHERE oi.id = d.id"
).bindparams(
    bindparam("ids", type_=ARRAY(PgUUID(as_uuid=True))),
    bindparam("paths", type_=ARRAY(Text)),
    bindparam("depths", type_=ARRAY(Integer)),
)
_REORDER = text(
    "UPDATE orcamento_item AS oi "
    "SET parent_id = d.parent_id, sort_order = d.sort_order "
    "FROM unnest(:ids, :parents, :orders) AS d(id, parent_id, sort_order) "
    "WHERE oi.id = d.id AND oi.versao_id = :vid"
).bindparams(
    bindparam("ids", type_=ARRAY(PgUUID(as_uuid=True))),
    bindparam("parents", type_=ARRAY(PgUUID(as_uuid=True))),
    bindparam("orders", type_=ARRAY(Integer)),
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _versao_editavel(session: Session, versao_id: uuid.UUID) -> None:
    """404 se a versão não existe (ou é de outro tenant, escondida pela RLS);
    409 se está travada (aprovada)."""
    row = (
        session.execute(
            text("SELECT is_locked FROM orcamento_versao WHERE id = :v"), {"v": versao_id}
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _VERSAO_NAO_ENCONTRADA
    if row["is_locked"]:
        raise _VERSAO_TRAVADA


def _versao_do_item(session: Session, item_id: uuid.UUID) -> uuid.UUID:
    """versao_id do item (404 se inexistente). Não checa lock — o chamador
    decide (leitura x escrita)."""
    row = session.execute(
        text("SELECT versao_id FROM orcamento_item WHERE id = :i"), {"i": item_id}
    ).first()
    if row is None:
        raise _ITEM_NAO_ENCONTRADO
    return row[0]  # type: ignore[no-any-return]


def _reindex_paths(session: Session, versao_id: uuid.UUID) -> None:
    """Recomputa path (cadeia de ids dos ancestrais + self) e depth de todos os
    itens da versão, varrendo a árvore a partir das raízes."""
    rows = (
        session.execute(
            text("SELECT id, parent_id FROM orcamento_item WHERE versao_id = :v"),
            {"v": versao_id},
        )
        .mappings()
        .all()
    )
    children: dict[uuid.UUID | None, list[uuid.UUID]] = defaultdict(list)
    for r in rows:
        children[r["parent_id"]].append(r["id"])

    ids: list[uuid.UUID] = []
    paths: list[str] = []
    depths: list[int] = []

    def walk(node_id: uuid.UUID, parent_path: str, depth: int) -> None:
        node_path = f"{parent_path}.{node_id}" if parent_path else str(node_id)
        ids.append(node_id)
        paths.append(node_path)
        depths.append(depth)
        for child in children.get(node_id, []):
            walk(child, node_path, depth + 1)

    for root in children.get(None, []):
        walk(root, "", 0)

    if ids:
        session.execute(_REINDEX, {"ids": ids, "paths": paths, "depths": depths})


def _tree(session: Session, versao_id: uuid.UUID) -> dict[str, Any]:
    """Monta o EapTree: agregados da versão + itens em ordem de árvore (path)."""
    versao = (
        session.execute(
            text(
                "SELECT id, is_locked, custo_direto, markup_global, taxa_adm, "
                "preco_venda, margem FROM orcamento_versao WHERE id = :v"
            ),
            {"v": versao_id},
        )
        .mappings()
        .first()
    )
    if versao is None:
        raise _VERSAO_NAO_ENCONTRADA
    itens = (
        session.execute(
            text(f"SELECT {_ITEM_COLUMNS} FROM orcamento_item WHERE versao_id = :v ORDER BY path"),
            {"v": versao_id},
        )
        .mappings()
        .all()
    )
    return {"versao": dict(versao), "itens": [dict(r) for r in itens]}


# --------------------------------------------------------------------------- #
# Operações
# --------------------------------------------------------------------------- #
def get_tree(session: Session, versao_id: uuid.UUID) -> dict[str, Any]:
    return _tree(session, versao_id)


def bulk_create(
    session: Session, *, company_id: str, versao_id: uuid.UUID, novos: list[ItemCreate]
) -> dict[str, Any]:
    _versao_editavel(session, versao_id)

    # Índice dos itens já existentes (para validar parent + tipo).
    existentes = {
        r["id"]: r["tipo"]
        for r in session.execute(
            text("SELECT id, tipo FROM orcamento_item WHERE versao_id = :v"),
            {"v": versao_id},
        ).mappings()
    }
    # Próximo sort_order por pai (append no fim do nível).
    next_ordem: dict[uuid.UUID | None, int] = defaultdict(int)
    for r in session.execute(
        text(
            "SELECT parent_id, COALESCE(MAX(sort_order), -1) + 1 AS prox "
            "FROM orcamento_item WHERE versao_id = :v GROUP BY parent_id"
        ),
        {"v": versao_id},
    ).mappings():
        next_ordem[r["parent_id"]] = r["prox"]

    params: list[dict[str, Any]] = []
    for item in novos:
        esperado = _PARENT_TIPO[item.tipo]
        if esperado is None:
            if item.parent_id is not None:
                raise _erro_parent(item.tipo, "fase não tem pai")
        else:
            if item.parent_id is None or existentes.get(item.parent_id) != esperado:
                raise _erro_parent(item.tipo, f"exige pai do tipo {esperado}")
        ordem = next_ordem[item.parent_id]
        next_ordem[item.parent_id] = ordem + 1
        params.append(
            {
                "cid": company_id,
                "vid": versao_id,
                "parent": item.parent_id,
                "tipo": item.tipo,
                "codigo": item.codigo,
                "descricao": item.descricao,
                "unidade": item.unidade,
                "qtd": item.quantidade,
                "preco": item.preco_unitario,
                "markup": item.markup_override,
                "ordem": ordem,
            }
        )

    session.execute(
        text(
            "INSERT INTO orcamento_item "
            "(company_id, versao_id, parent_id, tipo, codigo, descricao, unidade, "
            " quantidade, preco_unitario, markup_override, sort_order, path, depth) "
            "VALUES (:cid, :vid, :parent, :tipo, :codigo, :descricao, :unidade, "
            " :qtd, :preco, :markup, :ordem, '', 0)"
        ),
        params,
    )
    _reindex_paths(session, versao_id)
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def update_item(session: Session, *, item_id: uuid.UUID, patch: ItemUpdate) -> dict[str, Any]:
    versao_id = _versao_do_item(session, item_id)
    _versao_editavel(session, versao_id)

    campos = patch.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="nada para atualizar"
        )
    # `custo_total` é GENERATED; os demais são livres. Sem mudança estrutural →
    # sem reindex de path.
    sets = ", ".join(f"{col} = :{col}" for col in campos)
    session.execute(
        text(f"UPDATE orcamento_item SET {sets} WHERE id = :id"),
        {**campos, "id": item_id},
    )
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def delete_item(session: Session, *, item_id: uuid.UUID) -> dict[str, Any]:
    versao_id = _versao_do_item(session, item_id)
    _versao_editavel(session, versao_id)
    # A self-FK ON DELETE CASCADE remove a subárvore; o path dos demais itens
    # (cadeia de ancestrais) permanece válido — sem reindex.
    session.execute(text("DELETE FROM orcamento_item WHERE id = :id"), {"id": item_id})
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def duplicate_item(session: Session, *, company_id: str, item_id: uuid.UUID) -> dict[str, Any]:
    """Clona o item e toda a sua subárvore (novos ids), como irmão logo após o
    original."""
    versao_id = _versao_do_item(session, item_id)
    _versao_editavel(session, versao_id)

    rows = (
        session.execute(
            text(
                "SELECT id, parent_id, tipo, codigo, descricao, unidade, quantidade, "
                "preco_unitario, markup_override, sort_order "
                "FROM orcamento_item WHERE versao_id = :v"
            ),
            {"v": versao_id},
        )
        .mappings()
        .all()
    )
    by_id = {r["id"]: r for r in rows}
    children: dict[uuid.UUID | None, list[Any]] = defaultdict(list)
    for r in rows:
        children[r["parent_id"]].append(r)

    original = by_id.get(item_id)
    if original is None:
        raise _ITEM_NAO_ENCONTRADO

    # Novo sort_order: logo após o original (empurra os irmãos seguintes).
    session.execute(
        text(
            "UPDATE orcamento_item SET sort_order = sort_order + 1 "
            "WHERE versao_id = :v AND parent_id IS NOT DISTINCT FROM :p "
            "AND sort_order > :ordem"
        ),
        {"v": versao_id, "p": original["parent_id"], "ordem": original["sort_order"]},
    )

    inserts: list[dict[str, Any]] = []

    def clone(src: Any, new_parent: uuid.UUID | None, ordem: int) -> None:
        new_id = uuid.uuid4()
        inserts.append(
            {
                "id": new_id,
                "cid": company_id,
                "vid": versao_id,
                "parent": new_parent,
                "tipo": src["tipo"],
                "codigo": src["codigo"],
                "descricao": src["descricao"],
                "unidade": src["unidade"],
                "qtd": src["quantidade"],
                "preco": src["preco_unitario"],
                "markup": src["markup_override"],
                "ordem": ordem,
            }
        )
        for i, child in enumerate(children.get(src["id"], [])):
            clone(child, new_id, i)

    clone(original, original["parent_id"], original["sort_order"] + 1)
    session.execute(
        text(
            "INSERT INTO orcamento_item "
            "(id, company_id, versao_id, parent_id, tipo, codigo, descricao, unidade, "
            " quantidade, preco_unitario, markup_override, sort_order, path, depth) "
            "VALUES (:id, :cid, :vid, :parent, :tipo, :codigo, :descricao, :unidade, "
            " :qtd, :preco, :markup, :ordem, '', 0)"
        ),
        inserts,
    )
    _reindex_paths(session, versao_id)
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def reorder(session: Session, *, versao_id: uuid.UUID, ordem: list[ReorderItem]) -> dict[str, Any]:
    """Aplica novo (parent_id, sort_order) aos itens informados, revalida a
    hierarquia por tipo e reindexa paths. DnD entre níveis é permitido desde que
    respeite F→S→I."""
    _versao_editavel(session, versao_id)

    tipos = {
        r["id"]: r["tipo"]
        for r in session.execute(
            text("SELECT id, tipo FROM orcamento_item WHERE versao_id = :v"),
            {"v": versao_id},
        ).mappings()
    }
    for mov in ordem:
        if mov.id not in tipos:
            raise _ITEM_NAO_ENCONTRADO
        esperado = _PARENT_TIPO[tipos[mov.id]]
        if esperado is None:
            if mov.parent_id is not None:
                raise _erro_parent(tipos[mov.id], "fase não tem pai")
        elif mov.parent_id is None or tipos.get(mov.parent_id) != esperado:
            raise _erro_parent(tipos[mov.id], f"exige pai do tipo {esperado}")

    session.execute(
        _REORDER,
        {
            "vid": versao_id,
            "ids": [m.id for m in ordem],
            "parents": [m.parent_id for m in ordem],
            "orders": [m.sort_order for m in ordem],
        },
    )
    _reindex_paths(session, versao_id)
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def set_precificacao(
    session: Session, *, versao_id: uuid.UUID, markup_global: Any, taxa_adm: Any
) -> dict[str, Any]:
    _versao_editavel(session, versao_id)
    session.execute(
        text("UPDATE orcamento_versao SET markup_global = :mg, taxa_adm = :ta WHERE id = :v"),
        {"mg": markup_global, "ta": taxa_adm, "v": versao_id},
    )
    budget_calculator.recalcular(session, versao_id)
    return _tree(session, versao_id)


def _erro_parent(tipo: str, motivo: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"hierarquia inválida para tipo {tipo}: {motivo}",
    )


def tree_model(data: dict[str, Any]) -> EapTree:
    return EapTree.model_validate(data)
