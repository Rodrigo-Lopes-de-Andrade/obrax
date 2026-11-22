"""S-F3 — categorias e despesas (PRD US-F05, F06, F08, F09; ESPEC §5, §6.2; ERRATA E-08, E-10).

Roda sempre na sessão do request (`get_db`: role `app_user`, RLS ativa, GUC
`app.company_id` setada). Nenhuma query filtra `company_id` na mão: quem isola é a
RLS. O INSERT leva `company_id` explícito (NOT NULL + WITH CHECK da policy), e a FK
composta da E-08 é a rede de segurança caso uma validação aqui falhe. Não faz commit.

Dinheiro é `Decimal` de ponta a ponta; nada passa por `float`. Os `*Update` são lidos
com `model_dump(exclude_unset=True)`: campo omitido não vira `NULL`.

Auditoria (SEC-F07, CA-F09.4): o trigger `audit_despesa` (0033, função genérica da 0011)
grava `audit_log` em todo INSERT/UPDATE/DELETE, com autor e IP das GUCs de `get_db`. O
`action` é sempre `UPDATE` para uma mudança; o que distingue pagamento de edição é o diff
`before`/`after` (`status`, `data_pagamento`). O service não grava auditoria.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.financeiro.schemas import (
    CategoriaCreate,
    CategoriaUpdate,
    DespesaCreate,
    DespesaParceladaCreate,
    DespesaUpdate,
)

CATEGORIAS_PADRAO = (
    "Material",
    "Mão de obra",
    "Serviço de terceiro",
    "Equipamento",
    "Administrativo",
)

_CENTAVO = Decimal("0.01")

_NAO_ENCONTRADA = HTTPException(status.HTTP_404_NOT_FOUND, "despesa não encontrada")
_OBRA_NAO_ENCONTRADA = HTTPException(status.HTTP_404_NOT_FOUND, "obra não encontrada")


def _422(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


def _texto(valor: str, campo: str) -> str:
    """Texto obrigatório aparado; só espaços vira 422 (o Pydantic mede `min_length` ANTES
    do strip, então '   ' passa pelo schema). A CHECK `btrim(x) <> ''` é a rede no banco."""
    limpo = valor.strip()
    if not limpo:
        raise _422(f"{campo} não pode ser vazio")
    return limpo


def _hoje() -> date:
    """'Hoje' do negócio (fuso de Brasília): às 22h no Brasil o dia UTC já virou."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


# --------------------------------------------------------------------------- #
# Categorias
# --------------------------------------------------------------------------- #
_CAT_COLS = "id, nome, ativa, created_at"


def garantir_categorias_padrao(session: Session, company_id: str) -> None:
    """Seed das categorias padrão: uma vez por empresa, idempotente sob concorrência.

    Resolvido no banco, em três camadas:
    1. `pg_advisory_xact_lock` por empresa serializa os "primeiros acessos"
       simultâneos (de qualquer instância); o segundo espera o commit do primeiro e
       então vê as categorias;
    2. `WHERE NOT EXISTS` (qualquer linha da empresa, inclusive inativa) faz o seed
       valer só no primeiro acesso: renomear/desativar uma padrão não a recria;
    3. `ON CONFLICT (company_id, lower(nome)) WHERE deleted_at IS NULL DO NOTHING`
       (o índice único é parcial e com expressão, então `ON CONSTRAINT` não serve)
       é a rede de segurança se 1 e 2 falharem.
    Categoria nunca é apagada fisicamente (só desativada), então "existe alguma
    linha" é um marcador estável de "já semeado".
    """
    if session.execute(text("SELECT 1 FROM categoria_financeira LIMIT 1")).first() is not None:
        return  # caminho rápido; a corrida é resolvida abaixo, sob o lock
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended('categoria_financeira:' || :cid, 0))"),
        {"cid": company_id},
    )
    session.execute(
        text(
            "INSERT INTO categoria_financeira (company_id, nome) "
            "SELECT CAST(:cid AS uuid), n FROM unnest(CAST(:nomes AS text[])) AS n "
            "WHERE NOT EXISTS (SELECT 1 FROM categoria_financeira) "
            "ON CONFLICT (company_id, lower(nome)) WHERE deleted_at IS NULL DO NOTHING"
        ),
        {"cid": company_id, "nomes": list(CATEGORIAS_PADRAO)},
    )


def listar_categorias(
    session: Session, *, company_id: str, incluir_inativas: bool
) -> list[dict[str, Any]]:
    garantir_categorias_padrao(session, company_id)
    rows = (
        session.execute(
            text(
                f"SELECT {_CAT_COLS} FROM categoria_financeira "
                "WHERE deleted_at IS NULL AND (ativa OR CAST(:incl AS boolean)) "
                "ORDER BY lower(nome), id"
            ),
            {"incl": incluir_inativas},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def criar_categoria(
    session: Session, *, company_id: str, payload: CategoriaCreate
) -> dict[str, Any]:
    nome = _texto(payload.nome, "nome")
    garantir_categorias_padrao(session, company_id)
    row = (
        session.execute(
            text(
                "INSERT INTO categoria_financeira (company_id, nome) VALUES (:cid, :nome) "
                "ON CONFLICT (company_id, lower(nome)) WHERE deleted_at IS NULL DO NOTHING "
                f"RETURNING {_CAT_COLS}"
            ),
            {"cid": company_id, "nome": nome},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe categoria com esse nome")
    return dict(row)


def atualizar_categoria(
    session: Session, *, company_id: str, categoria_id: uuid.UUID, payload: CategoriaUpdate
) -> dict[str, Any]:
    garantir_categorias_padrao(session, company_id)
    campos = payload.model_dump(exclude_unset=True)
    if "nome" in campos:
        campos["nome"] = campos["nome"].strip()
        if not campos["nome"]:
            raise _422("nome não pode ser vazio")
    atual = (
        session.execute(
            text(
                f"SELECT {_CAT_COLS} FROM categoria_financeira "
                "WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": categoria_id},
        )
        .mappings()
        .first()
    )
    if atual is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "categoria não encontrada")
    if not campos:
        return dict(atual)
    sets = ", ".join(f"{c} = :{c}" for c in campos if c in ("nome", "ativa"))
    try:
        row = (
            session.execute(
                text(
                    f"UPDATE categoria_financeira SET {sets} WHERE id = :id RETURNING {_CAT_COLS}"
                ),
                {**campos, "id": categoria_id},
            )
            .mappings()
            .one()
        )
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe categoria com esse nome") from exc
    return dict(row)


# --------------------------------------------------------------------------- #
# Leitura de despesa
# --------------------------------------------------------------------------- #
_DESPESA_COLS = (
    "d.id, d.obra_id, d.obra_fase_id, f.descricao AS fase_descricao, d.categoria_id, "
    "c.nome AS categoria_nome, d.fornecedor_nome, d.fornecedor_id, d.descricao, d.valor, "
    "d.data_competencia, d.vencimento, d.status, d.data_pagamento, d.documento_id, "
    "d.grupo_parcelas_id, d.parcela_num, d.parcela_total, d.created_at, d.created_by"
)
_DESPESA_JOINS = (
    "JOIN obra_fase f ON f.id = d.obra_fase_id JOIN categoria_financeira c ON c.id = d.categoria_id"
)


def _obter(session: Session, despesa_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                f"SELECT {_DESPESA_COLS} FROM despesa d {_DESPESA_JOINS} "
                "WHERE d.id = :id AND d.deleted_at IS NULL"
            ),
            {"id": despesa_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NAO_ENCONTRADA
    return dict(row)


def obter_despesa(session: Session, despesa_id: uuid.UUID) -> dict[str, Any]:
    return _obter(session, despesa_id)


def listar_fases(session: Session, obra_id: uuid.UUID) -> list[dict[str, Any]]:
    """Fases da obra por `codigo`, inclusive as inativas (a tela filtra)."""
    _exigir_obra(session, obra_id)
    rows = (
        session.execute(
            text(
                "SELECT id, codigo, descricao, ativa FROM obra_fase "
                "WHERE obra_id = :o ORDER BY codigo, id"
            ),
            {"o": obra_id},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def listar_despesas(
    session: Session,
    *,
    obra_id: uuid.UUID,
    status_filter: str | None,
    obra_fase_id: uuid.UUID | None,
    categoria_id: uuid.UUID | None,
    de: date | None,
    ate: date | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    """Lista da obra, `id DESC` (UUIDv7 = mais nova primeiro), cursor por `id`.
    `de`/`ate` filtram `vencimento` (inclusivo nas duas pontas)."""
    cursor_id: uuid.UUID | None = None
    if cursor is not None:
        try:
            cursor_id = uuid.UUID(cursor)
        except ValueError as exc:
            raise _422("cursor inválido") from exc
    if de is not None and ate is not None and de > ate:
        raise _422("'de' não pode ser depois de 'ate'")
    _exigir_obra(session, obra_id)
    rows = (
        session.execute(
            text(
                f"SELECT {_DESPESA_COLS} FROM despesa d {_DESPESA_JOINS} "
                "WHERE d.obra_id = :obra_id AND d.deleted_at IS NULL "
                "  AND (CAST(:cursor AS uuid) IS NULL OR d.id < CAST(:cursor AS uuid)) "
                "  AND (CAST(:status AS despesa_status) IS NULL "
                "       OR d.status = CAST(:status AS despesa_status)) "
                "  AND (CAST(:fase AS uuid) IS NULL OR d.obra_fase_id = CAST(:fase AS uuid)) "
                "  AND (CAST(:cat AS uuid) IS NULL OR d.categoria_id = CAST(:cat AS uuid)) "
                "  AND (CAST(:de AS date) IS NULL OR d.vencimento >= CAST(:de AS date)) "
                "  AND (CAST(:ate AS date) IS NULL OR d.vencimento <= CAST(:ate AS date)) "
                "ORDER BY d.id DESC LIMIT :lim"
            ),
            {
                "obra_id": obra_id,
                "cursor": cursor_id,
                "status": status_filter,
                "fase": obra_fase_id,
                "cat": categoria_id,
                "de": de,
                "ate": ate,
                "lim": limit + 1,
            },
        )
        .mappings()
        .all()
    )
    tem_mais = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    return page, (str(page[-1]["id"]) if tem_mais else None)


# --------------------------------------------------------------------------- #
# Validações de referência (sob RLS: o que é de outro tenant "não existe")
# --------------------------------------------------------------------------- #
def _exigir_obra(session: Session, obra_id: uuid.UUID) -> None:
    ok = session.execute(
        text("SELECT 1 FROM obras WHERE id = :id AND deleted_at IS NULL"), {"id": obra_id}
    ).first()
    if ok is None:
        raise _OBRA_NAO_ENCONTRADA  # 404, nunca 403 (SEC-F04, ESPEC §7.5)


def _exigir_fase_da_obra(session: Session, obra_id: uuid.UUID, fase_id: uuid.UUID) -> None:
    ok = session.execute(
        text("SELECT 1 FROM obra_fase WHERE id = :f AND obra_id = :o"),
        {"f": fase_id, "o": obra_id},
    ).first()
    if ok is None:
        raise _422("fase não encontrada nesta obra")


def _exigir_categoria_ativa(session: Session, categoria_id: uuid.UUID) -> None:
    row = session.execute(
        text("SELECT ativa FROM categoria_financeira WHERE id = :id AND deleted_at IS NULL"),
        {"id": categoria_id},
    ).first()
    if row is None:
        raise _422("categoria não encontrada")
    if not row[0]:
        raise _422("categoria desativada não pode receber despesa nova")


def _exigir_documento_da_obra(
    session: Session, obra_id: uuid.UUID, documento_id: uuid.UUID
) -> None:
    ok = session.execute(
        text("SELECT 1 FROM documento WHERE id = :id AND obra_id = :o AND deleted_at IS NULL"),
        {"id": documento_id, "o": obra_id},
    ).first()
    if ok is None:
        raise _422("documento não encontrado nesta obra")


def _travar(session: Session, despesa_id: uuid.UUID) -> dict[str, Any]:
    row = (
        session.execute(
            text(
                "SELECT id, obra_id, status, obra_fase_id, categoria_id, documento_id "
                "FROM despesa WHERE id = :id AND deleted_at IS NULL FOR UPDATE"
            ),
            {"id": despesa_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise _NAO_ENCONTRADA
    return dict(row)


# --------------------------------------------------------------------------- #
# Criar
# --------------------------------------------------------------------------- #
_INSERT_DESPESA = (
    "INSERT INTO despesa (company_id, obra_id, obra_fase_id, categoria_id, fornecedor_nome, "
    "descricao, valor, data_competencia, vencimento, status, documento_id, "
    "grupo_parcelas_id, parcela_num, parcela_total, created_by) "
    "VALUES (:cid, :obra_id, :fase, :cat, :forn, :descr, :valor, :comp, :venc, "
    "CAST('prevista' AS despesa_status), :doc, :grupo, :pnum, :ptotal, :uid) RETURNING id"
)


def _validar_referencias(
    session: Session,
    obra_id: uuid.UUID,
    fase_id: uuid.UUID,
    categoria_id: uuid.UUID,
    documento_id: uuid.UUID | None,
) -> None:
    _exigir_obra(session, obra_id)
    _exigir_fase_da_obra(session, obra_id, fase_id)
    _exigir_categoria_ativa(session, categoria_id)
    if documento_id is not None:
        _exigir_documento_da_obra(session, obra_id, documento_id)


def _inserir(
    session: Session,
    *,
    company_id: str,
    user_id: str,
    obra_id: uuid.UUID,
    fase_id: uuid.UUID,
    categoria_id: uuid.UUID,
    fornecedor_nome: str,
    descricao: str,
    valor: Decimal,
    data_competencia: date,
    vencimento: date,
    documento_id: uuid.UUID | None,
    grupo: uuid.UUID | None = None,
    parcela_num: int | None = None,
    parcela_total: int | None = None,
) -> uuid.UUID:
    novo = session.execute(
        text(_INSERT_DESPESA),
        {
            "cid": company_id,
            "obra_id": obra_id,
            "fase": fase_id,
            "cat": categoria_id,
            "forn": fornecedor_nome,
            "descr": descricao,
            "valor": valor,
            "comp": data_competencia,
            "venc": vencimento,
            "doc": documento_id,
            "grupo": grupo,
            "pnum": parcela_num,
            "ptotal": parcela_total,
            "uid": user_id,
        },
    ).scalar_one()
    return novo  # type: ignore[no-any-return]


def criar_despesa(
    session: Session,
    *,
    company_id: str,
    user_id: str,
    obra_id: uuid.UUID,
    payload: DespesaCreate,
) -> dict[str, Any]:
    fornecedor = _texto(payload.fornecedor_nome, "fornecedor_nome")
    descricao = _texto(payload.descricao, "descricao")
    _validar_referencias(
        session, obra_id, payload.obra_fase_id, payload.categoria_id, payload.documento_id
    )
    novo = _inserir(
        session,
        company_id=company_id,
        user_id=user_id,
        obra_id=obra_id,
        fase_id=payload.obra_fase_id,
        categoria_id=payload.categoria_id,
        fornecedor_nome=fornecedor,
        descricao=descricao,
        valor=payload.valor,
        data_competencia=payload.data_competencia,
        vencimento=payload.vencimento,
        documento_id=payload.documento_id,
    )
    return _obter(session, novo)


# --------------------------------------------------------------------------- #
# Parcelamento (RN-F08)
# --------------------------------------------------------------------------- #
def somar_meses(base: date, meses: int) -> date:
    """`base` + `meses` meses, relativo à data original (31/jan → 28/fev → 31/mar);
    o dia é limitado ao último do mês de destino."""
    indice = base.year * 12 + (base.month - 1) + meses
    ano, mes = divmod(indice, 12)
    mes += 1
    return date(ano, mes, min(base.day, calendar.monthrange(ano, mes)[1]))


def dividir_em_parcelas(total: Decimal, n: int) -> list[Decimal]:
    """N parcelas em centavos que somam EXATAMENTE `total`; o resíduo vai na última.

    A parcela-base arredonda para BAIXO (`ROUND_DOWN`), não `HALF_UP`: assim o resíduo
    nunca é negativo e a última parcela nunca é menor que as outras. Com `HALF_UP`,
    0,05 em 10 parcelas daria 10 × 0,01 e uma última de -0,05. Parcela-base de zero
    centavo (valor < N centavos) é 422.
    """
    if n < 1:
        raise ValueError("n deve ser >= 1")
    base = (total / n).quantize(_CENTAVO, rounding=ROUND_DOWN)
    if base <= 0:
        raise _422(f"valor {total} é pequeno demais para {n} parcelas (mínimo de 0,01 cada)")
    parcelas = [base] * (n - 1)
    parcelas.append(total - base * (n - 1))
    if sum(parcelas, Decimal(0)) != total:  # invariante; nunca silenciada por `python -O`
        raise RuntimeError(f"divisão em parcelas não soma {total}: {parcelas}")
    return parcelas


def criar_despesa_parcelada(
    session: Session,
    *,
    company_id: str,
    user_id: str,
    obra_id: uuid.UUID,
    payload: DespesaParceladaCreate,
) -> tuple[uuid.UUID, list[dict[str, Any]]]:
    """N títulos independentes numa transação (a da request): se um falhar, nenhum
    fica. Herdam obra, fase, categoria, fornecedor, descrição, competência e NF;
    vencimentos mensais a partir de `primeiro_vencimento`."""
    fornecedor = _texto(payload.fornecedor_nome, "fornecedor_nome")
    descricao = _texto(payload.descricao, "descricao")
    _validar_referencias(
        session, obra_id, payload.obra_fase_id, payload.categoria_id, payload.documento_id
    )
    valores = dividir_em_parcelas(payload.valor, payload.numero_parcelas)
    # UUIDv7, como os demais ids do projeto (gerado pelo banco).
    grupo = session.execute(text("SELECT uuid_generate_v7()")).scalar_one()
    ids = [
        _inserir(
            session,
            company_id=company_id,
            user_id=user_id,
            obra_id=obra_id,
            fase_id=payload.obra_fase_id,
            categoria_id=payload.categoria_id,
            fornecedor_nome=fornecedor,
            descricao=descricao,
            valor=valor,
            data_competencia=payload.data_competencia,
            vencimento=somar_meses(payload.primeiro_vencimento, i),
            documento_id=payload.documento_id,
            grupo=grupo,
            parcela_num=i + 1,
            parcela_total=payload.numero_parcelas,
        )
        for i, valor in enumerate(valores)
    ]
    rows = (
        session.execute(
            text(
                f"SELECT {_DESPESA_COLS} FROM despesa d {_DESPESA_JOINS} "
                "WHERE d.id = ANY(CAST(:ids AS uuid[])) ORDER BY d.parcela_num"
            ),
            {"ids": ids},
        )
        .mappings()
        .all()
    )
    return grupo, [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Editar (parcial)
# --------------------------------------------------------------------------- #
# Campos que mexem no valor ou na apropriação: congelados fora de `prevista`
# (um `gestor` não pode alterar título já pago, que ele não consegue estornar).
_FINANCEIROS = frozenset(
    {"obra_fase_id", "categoria_id", "valor", "data_competencia", "vencimento"}
)
_COLUNAS_EDITAVEIS = _FINANCEIROS | {"fornecedor_nome", "descricao", "documento_id"}


def atualizar_despesa(
    session: Session,
    *,
    despesa_id: uuid.UUID,
    payload: DespesaUpdate,
) -> dict[str, Any]:
    """`exclude_unset=True`: só o que veio no body é gravado. Sem isso, cada PATCH
    gravaria `NULL` nos omitidos (500 nos NOT NULL; `documento_id` desvincularia a
    NF em silêncio)."""
    campos = payload.model_dump(exclude_unset=True)
    atual = _travar(session, despesa_id)
    if not campos:
        return _obter(session, despesa_id)

    if atual["status"] == "cancelada":
        raise _422("despesa cancelada é terminal e não pode ser editada")
    if atual["status"] != "prevista":
        congelados = sorted(set(campos) & _FINANCEIROS)
        if congelados:
            raise _422(
                f"despesa paga: {', '.join(congelados)} não pode mudar; "
                "estorne o pagamento primeiro"
            )

    for k in ("fornecedor_nome", "descricao"):
        if k in campos:
            campos[k] = campos[k].strip()
            if not campos[k]:
                raise _422(f"{k} não pode ser vazio")

    obra_id = atual["obra_id"]
    if "obra_fase_id" in campos:
        _exigir_fase_da_obra(session, obra_id, campos["obra_fase_id"])
    if "categoria_id" in campos and campos["categoria_id"] != atual["categoria_id"]:
        _exigir_categoria_ativa(session, campos["categoria_id"])
    if campos.get("documento_id") is not None:
        _exigir_documento_da_obra(session, obra_id, campos["documento_id"])

    colunas = [c for c in campos if c in _COLUNAS_EDITAVEIS]  # whitelist, nunca o input cru
    sets = ", ".join(f"{c} = :{c}" for c in colunas)
    session.execute(
        text(f"UPDATE despesa SET {sets} WHERE id = :id"),
        {**{c: campos[c] for c in colunas}, "id": despesa_id},
    )
    return _obter(session, despesa_id)


# --------------------------------------------------------------------------- #
# Máquina de estados (ESPEC §5): prevista -> paga -> prevista; prevista -> cancelada
# --------------------------------------------------------------------------- #
def _transicao(
    session: Session,
    *,
    despesa_id: uuid.UUID,
    de: str,
    sql_set: str,
    params: dict[str, Any],
    valida: str,
) -> dict[str, Any]:
    atual = _travar(session, despesa_id)
    if atual["status"] != de:
        raise _422(f"transição inválida: despesa está '{atual['status']}'; {valida}")
    session.execute(
        text(f"UPDATE despesa SET {sql_set} WHERE id = :id"), {**params, "id": despesa_id}
    )
    return _obter(session, despesa_id)


def pagar_despesa(
    session: Session, *, despesa_id: uuid.UUID, data_pagamento: date
) -> dict[str, Any]:
    if data_pagamento > _hoje():
        raise _422("data_pagamento não pode ser futura; agendamento é despesa prevista")
    return _transicao(
        session,
        despesa_id=despesa_id,
        de="prevista",
        sql_set="status = CAST('paga' AS despesa_status), data_pagamento = :dp",
        params={"dp": data_pagamento},
        valida="só despesa 'prevista' pode ser paga",
    )


def estornar_despesa(session: Session, *, despesa_id: uuid.UUID) -> dict[str, Any]:
    return _transicao(
        session,
        despesa_id=despesa_id,
        de="paga",
        sql_set="status = CAST('prevista' AS despesa_status), data_pagamento = NULL",
        params={},
        valida="só despesa 'paga' pode ser estornada",
    )


def cancelar_despesa(session: Session, *, despesa_id: uuid.UUID) -> dict[str, Any]:
    return _transicao(
        session,
        despesa_id=despesa_id,
        de="prevista",
        sql_set="status = CAST('cancelada' AS despesa_status)",
        params={},
        valida="só despesa 'prevista' pode ser cancelada (se paga, estorne antes)",
    )
