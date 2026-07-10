"""Montagem do pacote de exportação LGPD (B9.4, US-21).

Gera, em memória, um ZIP com todos os dados do tenant relevantes ao titular:
`clientes.json`, `obras.json`, `orcamentos.json`, `documentos.csv` e
`tickets.json` (SPRINTS B9.4). Roda sob `get_db` (RLS por `app.company_id`),
então as queries não filtram `company_id` na mão — a exportação já sai escopada
ao tenant.

Não há fila assíncrona no backend ainda (ver app/integrations/notifications.py),
então o pacote é montado de forma síncrona no request — mesma decisão do PDF do
orçamento. Os artefatos guardam Decimal como string (nunca float — docs/CLAUDE.md).
"""

from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _json_default(o: Any) -> str:
    if isinstance(o, datetime | date):
        return o.isoformat()
    if isinstance(o, uuid.UUID):
        return str(o)
    if isinstance(o, Decimal):
        return str(o)
    raise TypeError(f"não serializável: {type(o)!r}")


def _rows(session: Session, sql: str) -> list[dict[str, Any]]:
    return [dict(r) for r in session.execute(text(sql)).mappings().all()]


def _json_bytes(data: list[dict[str, Any]]) -> str:
    return json.dumps(data, default=_json_default, ensure_ascii=False, indent=2)


def _documentos_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "obra_id",
            "nome",
            "tipo",
            "categoria",
            "size_bytes",
            "visivel_cliente",
            "created_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["obra_id"],
                r["nome"],
                r["tipo"],
                r["categoria"] or "",
                r["size_bytes"] if r["size_bytes"] is not None else "",
                "sim" if r["visivel_cliente"] else "nao",
                r["created_at"].isoformat() if r["created_at"] else "",
            ]
        )
    return buf.getvalue()


def build_export_zip(session: Session) -> bytes:
    """Monta o ZIP de exportação do tenant corrente (RLS já ativa)."""
    clientes = _rows(
        session,
        "SELECT id, tipo_pessoa, documento, nome, telefone, email, created_at, deleted_at "
        "FROM clientes ORDER BY created_at",
    )
    obras = _rows(
        session,
        "SELECT id, cliente_id, codigo, nome, status, data_inicio, data_prevista_fim, "
        "data_real_fim, valor_contrato, created_at FROM obras ORDER BY created_at",
    )
    orcamentos = _rows(
        session,
        "SELECT o.id, o.obra_id, o.titulo, o.status, o.versao_atual, o.created_at, "
        "       v.preco_venda "
        "FROM orcamento o "
        "LEFT JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
        "WHERE o.deleted_at IS NULL ORDER BY o.created_at",
    )
    documentos = _rows(
        session,
        "SELECT id, obra_id, nome, tipo, categoria, size_bytes, visivel_cliente, created_at "
        "FROM documento WHERE deleted_at IS NULL ORDER BY created_at",
    )
    tickets = _rows(
        session,
        "SELECT id, obra_id, titulo, descricao, status, created_at "
        "FROM ticket WHERE deleted_at IS NULL ORDER BY created_at",
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("clientes.json", _json_bytes(clientes))
        zf.writestr("obras.json", _json_bytes(obras))
        zf.writestr("orcamentos.json", _json_bytes(orcamentos))
        zf.writestr("documentos.csv", _documentos_csv(documentos))
        zf.writestr("tickets.json", _json_bytes(tickets))
    return buffer.getvalue()
