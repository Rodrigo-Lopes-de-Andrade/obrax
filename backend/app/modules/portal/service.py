"""Regras de negócio do portal do cliente (B9.2 leitura, B9.3 aprovação).

Origens de tenant distintas:
- `mint_portal_link` roda sob `get_db` (admin autenticado, RLS pelo JWT de
  acesso): valida a obra do tenant e emite o token do portal (escopo = 1 obra).
- as demais rodam sob `get_portal_db` (RLS pelo token do portal): leem o
  andamento da obra e o orçamento vigente, e registram a decisão do cliente —
  nada de custo/markup/margem internos (SPRINTS B9.2), só o preço final.

A aprovação/rejeição grava `orcamento_aprovacao` (evidência: comentário,
assinatura, IP), muda o status do orçamento (o trigger `audit_orcamento` loga a
transição com IP) e notifica os gestores (best-effort). `storage_path`/
`assinatura_path` guardam só a chave; URLs são assinadas sob demanda.
"""

from __future__ import annotations

import base64
import binascii
import logging
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_portal_token
from app.integrations.notifications import EmailMessage, Notifier, notify_safe
from app.integrations.storage import StorageClient
from app.modules.portal.schemas import PortalAprovacaoIn

logger = logging.getLogger("app.portal")

# TTL das URLs de download do portal — curto, re-assinadas a cada leitura.
_DOWNLOAD_TTL_SECONDS = 900

_OBRA_NAO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="obra não encontrada"
)
_SEM_ORCAMENTO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="nenhum orçamento disponível para o cliente nesta obra",
)
_NAO_AGUARDA = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="orçamento não está aguardando aprovação",
)


def mint_portal_link(session: Session, *, company_id: str, obra_id: uuid.UUID) -> dict[str, Any]:
    """Emite o link do portal para uma obra do tenant (admin). 404 se a obra
    não existe/for de outro tenant (escondida pela RLS)."""
    row = (
        session.execute(
            text("SELECT cliente_id FROM obras WHERE id = :id AND deleted_at IS NULL"),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _OBRA_NAO_ENCONTRADA

    issued = create_portal_token(
        company_id=uuid.UUID(company_id),
        obra_id=obra_id,
        cliente_id=row["cliente_id"],
    )
    return {
        "token": issued.token,
        "url": f"/obra/{issued.token}",
        "expires_at": issued.expires_at,
    }


def _sign(storage: StorageClient, key: str | None) -> str | None:
    return storage.presigned_get_url(key=key, expires_in=_DOWNLOAD_TTL_SECONDS) if key else None


def get_portal_obra(
    session: Session, storage: StorageClient, *, obra_id: uuid.UUID
) -> dict[str, Any]:
    """Timeline read-only da obra: dados de andamento + docs visíveis + fotos."""
    obra = (
        session.execute(
            text(
                "SELECT o.id, o.codigo, o.nome, o.status, o.data_inicio, o.data_prevista_fim, "
                "       c.razao_social AS construtora "
                "FROM obras o JOIN companies c ON c.id = o.company_id "
                "WHERE o.id = :id AND o.deleted_at IS NULL"
            ),
            {"id": obra_id},
        )
        .mappings()
        .first()
    )
    if obra is None:
        raise _OBRA_NAO_ENCONTRADA

    documentos = [
        {
            "id": d["id"],
            "nome": d["nome"],
            "tipo": d["tipo"],
            "categoria": d["categoria"],
            "created_at": d["created_at"],
            "download_url": _sign(storage, d["storage_path"]),
        }
        for d in session.execute(
            text(
                "SELECT id, nome, tipo, categoria, created_at, storage_path FROM documento "
                "WHERE obra_id = :obra_id AND visivel_cliente = true "
                "  AND deleted_at IS NULL AND storage_path IS NOT NULL "
                "ORDER BY id DESC"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .all()
    ]

    fotos = [
        {
            "id": f["id"],
            "captured_at": f["captured_at"],
            "download_url": _sign(storage, f["storage_path"]),
        }
        for f in session.execute(
            text(
                "SELECT id, captured_at, storage_path FROM photo "
                "WHERE obra_id = :obra_id AND sync_status = 'sincronizado' "
                "  AND deleted_at IS NULL "
                "ORDER BY id DESC"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .all()
    ]

    return {
        "id": obra["id"],
        "codigo": obra["codigo"],
        "nome": obra["nome"],
        "status": obra["status"],
        "data_inicio": obra["data_inicio"],
        "data_prevista_fim": obra["data_prevista_fim"],
        "construtora": obra["construtora"],
        "documentos": documentos,
        "fotos": fotos,
    }


def _current_orcamento(session: Session, obra_id: uuid.UUID) -> Any:
    """Orçamento vigente que o cliente pode ver: o mais recente da obra que já
    saiu do rascunho (aguardando_aprovacao/aprovado/rejeitado)."""
    return (
        session.execute(
            text(
                "SELECT o.id, o.titulo, o.status, v.id AS versao_id, v.preco_venda, "
                "       v.pdf_storage_path "
                "FROM orcamento o "
                "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
                "WHERE o.obra_id = :obra_id AND o.deleted_at IS NULL "
                "  AND o.status IN ('aguardando_aprovacao','aprovado','rejeitado') "
                "ORDER BY o.id DESC LIMIT 1"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .first()
    )


def _orcamento_out(session: Session, storage: StorageClient, row: Any) -> dict[str, Any]:
    decisao = (
        session.execute(
            text(
                "SELECT decisao, created_at FROM orcamento_aprovacao "
                "WHERE orcamento_id = :oid ORDER BY id DESC LIMIT 1"
            ),
            {"oid": row["id"]},
        )
        .mappings()
        .first()
    )
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "status": row["status"],
        "preco_venda": row["preco_venda"],
        "pdf_url": _sign(storage, row["pdf_storage_path"]),
        "decisao": decisao["decisao"] if decisao else None,
        "decidido_em": decisao["created_at"] if decisao else None,
    }


def get_portal_orcamento(
    session: Session, storage: StorageClient, *, obra_id: uuid.UUID
) -> dict[str, Any]:
    row = _current_orcamento(session, obra_id)
    if row is None:
        raise _SEM_ORCAMENTO
    return _orcamento_out(session, storage, row)


_TICKET_NAO_ENCONTRADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="chamado não encontrado nesta obra"
)
_TICKET_FECHADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="chamado fechado não aceita novas mensagens"
)


def list_portal_tickets(session: Session, *, obra_id: uuid.UUID) -> list[dict[str, Any]]:
    """Chamados da obra (US-19), cada um com o histórico de mensagens em ordem
    cronológica. Escopado à obra do token — a RLS já isola o tenant, e o filtro
    `obra_id` restringe à obra do link (um cliente não vê chamados de outras
    obras do mesmo tenant)."""
    tickets = (
        session.execute(
            text(
                "SELECT id, titulo, status, created_at FROM ticket "
                "WHERE obra_id = :obra_id AND deleted_at IS NULL "
                "ORDER BY created_at DESC"
            ),
            {"obra_id": obra_id},
        )
        .mappings()
        .all()
    )
    if not tickets:
        return []

    msgs_por_ticket: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for m in (
        session.execute(
            text(
                "SELECT id, ticket_id, author_id, content, attachment_paths, created_at "
                "FROM ticket_mensagem WHERE ticket_id = ANY(:ids) "
                "ORDER BY created_at ASC, id ASC"
            ),
            {"ids": [t["id"] for t in tickets]},
        )
        .mappings()
        .all()
    ):
        msgs_por_ticket.setdefault(m["ticket_id"], []).append(dict(m))

    return [{**dict(t), "mensagens": msgs_por_ticket.get(t["id"], [])} for t in tickets]


def add_portal_mensagem(
    session: Session,
    notifier: Notifier,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    ticket_id: uuid.UUID,
    content: str,
) -> dict[str, Any]:
    """Registra uma mensagem do cliente num chamado (US-19). `author_id` NULL
    marca a autoria do cliente (o front alinha à direita). 404 se o chamado não
    for desta obra; 409 se estiver fechado. Notifica os gestores (best-effort)."""
    ticket = (
        session.execute(
            text(
                "SELECT titulo, status FROM ticket "
                "WHERE id = :tid AND obra_id = :obra_id AND deleted_at IS NULL"
            ),
            {"tid": ticket_id, "obra_id": obra_id},
        )
        .mappings()
        .first()
    )
    if ticket is None:
        raise _TICKET_NAO_ENCONTRADO
    if ticket["status"] == "fechado":
        raise _TICKET_FECHADO

    row = (
        session.execute(
            text(
                "INSERT INTO ticket_mensagem (company_id, ticket_id, author_id, content) "
                "VALUES (:c, :tid, NULL, :content) "
                "RETURNING id, ticket_id, author_id, content, attachment_paths, created_at"
            ),
            {"c": company_id, "tid": ticket_id, "content": content},
        )
        .mappings()
        .one()
    )
    _notify_gestores(
        session,
        notifier,
        company_id=company_id,
        assunto=f"Nova mensagem do cliente no chamado '{ticket['titulo']}'",
    )
    return dict(row)


def _decode_assinatura(data_url: str) -> bytes:
    """Aceita `data:image/...;base64,<b64>` ou base64 cru. 422 se inválido."""
    b64 = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="assinatura inválida"
        ) from exc


def _notify_gestores(
    session: Session, notifier: Notifier, *, company_id: str, assunto: str
) -> None:
    """Best-effort: avisa owners/admins/gestores da decisão. Nunca derruba a
    aprovação — qualquer falha (RLS, envio) é logada e engolida."""
    try:
        emails = (
            session.execute(
                text(
                    "SELECT u.email FROM users u "
                    "JOIN user_company_role ucr ON ucr.user_id = u.id "
                    "WHERE ucr.company_id = :cid "
                    "  AND ucr.role IN ('owner','admin','gestor') AND u.deleted_at IS NULL"
                ),
                {"cid": company_id},
            )
            .scalars()
            .all()
        )
    except Exception:  # noqa: BLE001 — notificação é best-effort (B4.5)
        logger.warning("falha ao buscar gestores para notificar", exc_info=True)
        return
    notify_safe(
        notifier,
        EmailMessage(to=tuple(str(e) for e in emails), subject=assunto, body=assunto),
    )


def decide_orcamento(
    session: Session,
    storage: StorageClient,
    notifier: Notifier,
    *,
    company_id: str,
    obra_id: uuid.UUID,
    decisao: str,
    payload: PortalAprovacaoIn,
) -> dict[str, Any]:
    """Registra a decisão do cliente (aprovar/rejeitado) sobre o orçamento
    vigente: grava evidência (comentário/assinatura/IP), muda o status e, se
    aprovado, trava a versão. Só age sobre orçamento `aguardando_aprovacao`."""
    row = _current_orcamento(session, obra_id)
    if row is None:
        raise _SEM_ORCAMENTO
    if row["status"] != "aguardando_aprovacao":
        raise _NAO_AGUARDA

    assinatura_path: str | None = None
    if payload.assinatura:
        raw = _decode_assinatura(payload.assinatura)
        assinatura_path = f"{company_id}/aprovacoes/{uuid.uuid4()}.png"
        storage.put_object(key=assinatura_path, body=raw, content_type="image/png")

    # IP vem da mesma GUC que o trigger de auditoria lê (app.client_ip), setada
    # no get_portal_db — mantém a evidência consistente entre as duas trilhas.
    session.execute(
        text(
            "INSERT INTO orcamento_aprovacao "
            "(company_id, orcamento_id, versao_id, decisao, comentario, assinatura_path, "
            " assinado_por, ip) "
            "VALUES (:c, :oid, :vid, CAST(:decisao AS aprovacao_decisao), :comentario, "
            " :assinatura_path, :assinado_por, "
            " NULLIF(current_setting('app.client_ip', true), '')::inet)"
        ),
        {
            "c": company_id,
            "oid": row["id"],
            "vid": row["versao_id"],
            "decisao": decisao,
            "comentario": payload.comentario,
            "assinatura_path": assinatura_path,
            "assinado_por": payload.assinado_por,
        },
    )

    novo_status = "aprovado" if decisao == "aprovado" else "rejeitado"
    session.execute(
        text("UPDATE orcamento SET status = CAST(:s AS orcamento_status) WHERE id = :oid"),
        {"s": novo_status, "oid": row["id"]},
    )
    if decisao == "aprovado":
        # Versão aprovada vira snapshot imutável (trigger de banco é o backstop).
        session.execute(
            text("UPDATE orcamento_versao SET is_locked = true WHERE id = :vid"),
            {"vid": row["versao_id"]},
        )

    _notify_gestores(
        session,
        notifier,
        company_id=company_id,
        assunto=f"Orçamento '{row['titulo']}' {novo_status} pelo cliente",
    )

    atual = _current_orcamento(session, obra_id)
    return _orcamento_out(session, storage, atual)
