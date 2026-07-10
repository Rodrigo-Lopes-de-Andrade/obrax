"""B6.3 — geração do PDF do orçamento (US-17).

Monta o contexto tipado do template (B6.4) a partir do banco — empresa, cliente,
obra, versão atual e a EAP em ordem de árvore —, renderiza o HTML timbrado,
converte via `PdfRenderer` (dev = HTML; prod = sidecar Puppeteer) e sobe o
artefato no object store. Persiste **só a chave** (`pdf_storage_path`), nunca a
URL: o download é assinado sob demanda no GET (TTL 1h). Regra do projeto:
anexos são storage paths, nunca URLs (docs/CLAUDE.md).

Geração é **síncrona** hoje (roda na request do POST). Seam de fila: quando
houver arq, o POST só enfileira este job e o GET faz poll do `pdf_gerado_em` —
o contrato do frontend (POST → poll) já é compatível. Mesmo padrão
sync-com-TODO de integrations/notifications.py.

Curva ABC e resumo por fase saem dos campos **denormalizados** da versão
(`curva_abc_json` / `markup_por_fase_json`, B6.1/B6.2), mantidos frescos pelo
recálculo a cada mutação — o job só lê, não recalcula. Versão sem itens (JSON
nulo) gera um PDF com as seções vazias, sem quebrar.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.pdf import PdfRenderer
from app.integrations.storage import StorageClient
from app.modules.orcamento.pdf.template import (
    OrcamentoPdfContext,
    PdfAbcClasse,
    PdfEmpresa,
    PdfFaseResumo,
    PdfLinhaEap,
    render_orcamento_html,
)

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="orçamento não encontrado")
_PDF_NAO_GERADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="PDF ainda não foi gerado"
)

# Orçamento + versão atual + empresa/cliente/obra. `emitido_em` já formatado no
# fuso da empresa (dd/mm/aaaa) — o template recebe a string pronta.
_LOAD = text(
    "SELECT "
    "  o.company_id, o.titulo, o.status, "
    "  c.razao_social AS empresa_nome, "
    "  cl.nome AS cliente_nome, cl.documento AS cliente_documento, "
    "  ob.codigo AS obra_codigo, ob.nome AS obra_nome, "
    "  v.id AS versao_id, v.numero AS revisao, "
    "  v.custo_direto, v.markup_global, v.taxa_adm, v.preco_venda, v.margem, "
    "  v.curva_abc_json, v.markup_por_fase_json, "
    "  to_char(timezone(c.timezone, now()), 'DD/MM/YYYY') AS emitido_em "
    "FROM orcamento o "
    "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
    "JOIN obras ob ON ob.id = o.obra_id "
    "JOIN clientes cl ON cl.id = ob.cliente_id "
    "JOIN companies c ON c.id = o.company_id "
    "WHERE o.id = :id AND o.deleted_at IS NULL"
)
# EAP em ordem de árvore — mesmo ORDER BY path do builder (services/itens.py),
# pro PDF espelhar exatamente o que o usuário vê na tela.
_LOAD_ITENS = text(
    "SELECT tipo, depth, codigo, descricao, unidade, quantidade, preco_unitario, subtotal "
    "FROM orcamento_item WHERE versao_id = :vid ORDER BY path"
)
_UPDATE_PDF = text(
    "UPDATE orcamento_versao SET pdf_storage_path = :key, pdf_gerado_em = now() "
    "WHERE id = :vid RETURNING pdf_gerado_em"
)
_LOAD_PDF = text(
    "SELECT v.pdf_storage_path, v.pdf_gerado_em FROM orcamento o "
    "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
    "WHERE o.id = :id AND o.deleted_at IS NULL"
)


def _content_type_for(key: str) -> str:
    """Content-type derivado da extensão da chave (pdf em prod, html em dev)."""
    return "application/pdf" if key.endswith(".pdf") else "text/html; charset=utf-8"


def _build_context(row: Any, item_rows: list[Any]) -> OrcamentoPdfContext:
    linhas = [
        PdfLinhaEap(
            tipo=r["tipo"],
            depth=r["depth"],
            codigo=r["codigo"],
            descricao=r["descricao"],
            unidade=r["unidade"],
            quantidade=r["quantidade"],
            preco_unitario=r["preco_unitario"],
            subtotal=r["subtotal"],
        )
        for r in item_rows
    ]

    # Resumo por fase (denormalizado). `pct` = participação da fase na soma dos
    # subtotais das fases (fecha em 100%); valores vêm como string no JSON.
    fases_raw: list[dict[str, Any]] = row["markup_por_fase_json"] or []
    total_fases = sum((Decimal(f["subtotal"]) for f in fases_raw), Decimal(0))
    fases = [
        PdfFaseResumo(
            descricao=f"{f['codigo']} — {f['descricao']}" if f.get("codigo") else f["descricao"],
            custo=Decimal(f["custo"]),
            markup=Decimal(f["markup"]),
            subtotal=Decimal(f["subtotal"]),
            pct=(Decimal(f["subtotal"]) / total_fases) if total_fases > 0 else Decimal(0),
        )
        for f in fases_raw
    ]

    abc_raw: dict[str, Any] | None = row["curva_abc_json"]
    abc = [
        PdfAbcClasse(
            classe=c["classe"],
            count=c["count"],
            custo=Decimal(c["custo"]),
            pct=Decimal(c["pct"]),
        )
        for c in (abc_raw or {}).get("classes", [])
    ]

    return OrcamentoPdfContext(
        empresa=PdfEmpresa(nome=row["empresa_nome"]),
        cliente_nome=row["cliente_nome"],
        cliente_documento=row["cliente_documento"],
        obra_codigo=row["obra_codigo"],
        obra_nome=row["obra_nome"],
        titulo=row["titulo"],
        revisao=row["revisao"],
        status=row["status"],
        emitido_em=row["emitido_em"],
        custo_direto=row["custo_direto"],
        markup_global=row["markup_global"],
        taxa_adm=row["taxa_adm"],
        preco_venda=row["preco_venda"],
        margem=row["margem"],
        linhas=linhas,
        fases=fases,
        abc=abc,
    )


def gerar_pdf(
    session: Session,
    *,
    storage: StorageClient,
    renderer: PdfRenderer,
    orcamento_id: uuid.UUID,
) -> dict[str, Any]:
    """Gera o PDF da versão atual, sobe no storage e grava a chave + timestamp.
    Não faz commit — o chamador controla a transação."""
    row = session.execute(_LOAD, {"id": orcamento_id}).mappings().first()
    if row is None:
        raise _NOT_FOUND
    item_rows = session.execute(_LOAD_ITENS, {"vid": row["versao_id"]}).mappings().all()

    ctx = _build_context(row, list(item_rows))
    rendered = renderer.render(html=render_orcamento_html(ctx))

    # Chave por versão: regerar sobrescreve o artefato da mesma revisão.
    key = f"{row['company_id']}/orcamentos/{orcamento_id}/{row['versao_id']}.{rendered.extension}"
    storage.put_object(key=key, body=rendered.body, content_type=rendered.content_type)

    gerado_em = session.execute(_UPDATE_PDF, {"key": key, "vid": row["versao_id"]}).scalar_one()
    return {"gerado_em": gerado_em, "content_type": rendered.content_type}


def get_pdf_status(
    session: Session,
    *,
    storage: StorageClient,
    orcamento_id: uuid.UUID,
    ttl: int,
) -> dict[str, Any]:
    """Metadados do PDF da versão atual + URL de download assinada (TTL curto).
    404 se o orçamento não existe ou o PDF ainda não foi gerado."""
    row = session.execute(_LOAD_PDF, {"id": orcamento_id}).mappings().first()
    if row is None:
        raise _NOT_FOUND
    key: str | None = row["pdf_storage_path"]
    if key is None or row["pdf_gerado_em"] is None:
        raise _PDF_NAO_GERADO
    return {
        "gerado_em": row["pdf_gerado_em"],
        "content_type": _content_type_for(key),
        "download_url": storage.presigned_get_url(key=key, expires_in=ttl),
    }
