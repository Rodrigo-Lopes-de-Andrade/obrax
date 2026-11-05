"""S-F1 — sincronização de `obra_fase` com a versão de orçamento aprovada.

`obra_fase` é a identidade estável da fase da obra (ESPEC §4, RN-F03): a
despesa aponta para ela, não para `orcamento_item`, que muda de ID a cada
revisão. A cada aprovação o orçamento se reconcilia nela por `codigo`:

- código novo            → cria a fase;
- código já existente    → atualiza descrição, valor orçado, ordem e rastreio
                           (o `id` é preservado);
- código que sumiu       → `ativa = false` (nunca apaga: pode ter despesa).

Um orçamento aprovado por obra (ERRATA E-07): aprovar outro orçamento da mesma
obra é 409. A obra é travada (`SELECT ... FOR NO KEY UPDATE`, sob RLS) antes de ler
ou escrever fases, serializando aprovações concorrentes; não bloqueia inserts
filhos da obra (fotos, chamados), que pegam só `FOR KEY SHARE` pela FK.

Chamado pelos DOIS pontos de aprovação (ESPEC §4.1): `PATCH
/orcamentos/{id}/status` e a decisão do cliente no portal. Roda na sessão e na
transação do chamador (`app_user`, GUC `app.company_id` já setada) — a RLS de
`obra_fase` (policy com WITH CHECK) é quem garante o tenant; nada aqui filtra
`company_id` na mão nem usa outra role. Não faz commit.

`valor_orcado` = custo direto agregado da fase: soma do `custo_total`
(quantidade × preço unitário, sem markup) das folhas da subárvore da fase — a
mesma definição do `BudgetCalculator`. Tudo `Decimal`/NUMERIC.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

# Fases (tipo 'F') da versão com o custo direto agregado da subárvore: folha =
# item sem filhos (igual ao BudgetCalculator); uma fase sem filhos é folha de si.
_FASES_DA_VERSAO = text(
    """
    WITH RECURSIVE arvore AS (
        SELECT id AS fase_id, id AS no_id
        FROM orcamento_item
        WHERE versao_id = :vid AND tipo = 'F'
      UNION ALL
        SELECT a.fase_id, c.id
        FROM arvore a
        JOIN orcamento_item c ON c.parent_id = a.no_id
    )
    SELECT f.id, f.codigo, f.descricao, f.sort_order,
           COALESCE(SUM(n.custo_total) FILTER (
               WHERE NOT EXISTS (SELECT 1 FROM orcamento_item k WHERE k.parent_id = n.id)
           ), 0) AS custo_direto
    FROM orcamento_item f
    LEFT JOIN arvore a ON a.fase_id = f.id
    LEFT JOIN orcamento_item n ON n.id = a.no_id
    WHERE f.versao_id = :vid AND f.tipo = 'F'
    GROUP BY f.id, f.codigo, f.descricao, f.sort_order
    ORDER BY f.sort_order, f.id
    """
)

_UPSERT_FASE = text(
    """
    INSERT INTO obra_fase
        (company_id, obra_id, codigo, descricao, valor_orcado, sort_order, ativa,
         orcamento_versao_id)
    VALUES (:cid, :obra_id, :codigo, :descricao, :valor, :sort_order, true, :vid)
    ON CONFLICT (obra_id, codigo) DO UPDATE SET
        descricao = EXCLUDED.descricao,
        valor_orcado = EXCLUDED.valor_orcado,
        sort_order = EXCLUDED.sort_order,
        ativa = true,
        orcamento_versao_id = EXCLUDED.orcamento_versao_id
    """
)


def codigo_da_fase(codigo: str | None, sort_order: int) -> str:
    """Código de reconciliação: o do orçamento, ou o sintético `F{ordem:03d}`
    quando a fase não tem código (ESPEC §4.3)."""
    limpo = (codigo or "").strip()
    return limpo if limpo else f"F{sort_order:03d}"


def _travar_obra(session: Session, obra_id: uuid.UUID) -> None:
    """Serializa por obra (E-07). Sob RLS: obra de outro tenant não é travada."""
    session.execute(text("SELECT id FROM obras WHERE id = :o FOR NO KEY UPDATE"), {"o": obra_id})


def _orcamento_e_versao(session: Session, orcamento_id: uuid.UUID) -> Any:
    row = (
        session.execute(
            text(
                "SELECT o.company_id, o.obra_id, o.status, v.id AS versao_id "
                "FROM orcamento o "
                "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
                "WHERE o.id = :id AND o.deleted_at IS NULL"
            ),
            {"id": orcamento_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="orçamento não encontrado"
        )
    return row


def _fases_por_codigo(session: Session, versao_id: uuid.UUID) -> dict[str, list[Any]]:
    """Fases da versão por código de reconciliação; 422 nomeando as fases se
    houver código repetido (inclui colisão com o sintético `F{ordem:03d}`)."""
    fases = session.execute(_FASES_DA_VERSAO, {"vid": versao_id}).mappings().all()
    por_codigo: dict[str, list[Any]] = defaultdict(list)
    for f in fases:
        por_codigo[codigo_da_fase(f["codigo"], f["sort_order"])].append(f)

    duplicados = {c: fs for c, fs in por_codigo.items() if len(fs) > 1}
    if duplicados:
        partes = [
            f"código '{c}': " + ", ".join(f"'{f['descricao']}'" for f in fs)
            for c, fs in duplicados.items()
        ]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fases com o mesmo código no orçamento — " + "; ".join(partes),
        )
    return por_codigo


def validar_aprovacao(session: Session, orcamento_id: uuid.UUID) -> None:
    """Tudo o que pode recusar uma aprovação, sem escrever (E-07 + §4.3):
    409 se a obra já tem OUTRO orçamento aprovado; 422 se há fases duplicadas.
    Chamar antes de qualquer efeito colateral (ex.: gravar assinatura). Usada
    também na ida para `aguardando_aprovacao` (mesma regra, E-07 decorrência)."""
    alvo = _orcamento_e_versao(session, orcamento_id)
    _travar_obra(session, alvo["obra_id"])
    outro = session.execute(
        text(
            "SELECT titulo FROM orcamento "
            "WHERE obra_id = :o AND id <> :id AND status = 'aprovado' AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"o": alvo["obra_id"], "id": orcamento_id},
    ).first()
    if outro is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"a obra já tem um orçamento aprovado ('{outro[0]}'); "
                "para alterar o valor, crie uma nova versão dele"
            ),
        )
    _fases_por_codigo(session, alvo["versao_id"])


def sincronizar_fases(session: Session, orcamento_id: uuid.UUID) -> None:
    """Reconcilia `obra_fase` da obra com a versão aprovada (`versao_atual` com
    `orcamento.status = 'aprovado'`, ESPEC §4.2). 409 se o orçamento não está
    aprovado; 422 nomeando as fases se houver código repetido na versão."""
    obra_id = _orcamento_e_versao(session, orcamento_id)["obra_id"]
    _travar_obra(session, obra_id)  # antes de ler/escrever fases (E-07)
    alvo = (
        session.execute(
            text(
                "SELECT o.company_id, o.obra_id, v.id AS versao_id "
                "FROM orcamento o "
                "JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual "
                "WHERE o.id = :id AND o.deleted_at IS NULL AND o.status = 'aprovado'"
            ),
            {"id": orcamento_id},
        )
        .mappings()
        .first()
    )
    if alvo is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="orçamento sem versão aprovada: não há o que sincronizar",
        )

    por_codigo = _fases_por_codigo(session, alvo["versao_id"])

    for codigo, (f,) in por_codigo.items():
        valor: Decimal = f["custo_direto"]
        session.execute(
            _UPSERT_FASE,
            {
                "cid": alvo["company_id"],
                "obra_id": alvo["obra_id"],
                "codigo": codigo,
                "descricao": f["descricao"],
                "valor": valor,
                "sort_order": f["sort_order"],
                "vid": alvo["versao_id"],
            },
        )

    # Sumiu da versão aprovada → inativa, nunca apagada.
    session.execute(
        text(
            "UPDATE obra_fase SET ativa = false "
            "WHERE obra_id = :obra_id AND ativa AND NOT (codigo = ANY(CAST(:codigos AS text[])))"
        ),
        {"obra_id": alvo["obra_id"], "codigos": list(por_codigo.keys())},
    )
