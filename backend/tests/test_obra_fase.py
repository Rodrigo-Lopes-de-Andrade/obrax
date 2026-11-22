"""S-F1 — sincronização de `obra_fase` na aprovação de versão de orçamento.

Os testes de rota chamam as DUAS rotas reais de aprovação (ESPEC §4.1):
`PATCH /orcamentos/{id}/status` e `POST /portal/orcamentos/{token}/aprovar`.
A reconciliação da segunda versão (RN-F03) monta a versão 2 por SQL — a US-16
não existe (ESPEC §4.5) — e chama o service: ela valida a reconciliação, não o
disparo. O disparo é coberto pelos testes de rota.

Valores de `valor_orcado` conferidos contra cálculo à mão (Decimal exato):
    Fundações  S1: 3,5 × 12,34 = 43,19 ; 2 × 100,55 = 201,10
               S2: 1,25 × 80,40 = 100,50                       → 344,79
    Estrutura  3 × 0,335 = 1,005 → 1,01 (meio centavo p/ cima)
               7 × 19,99 = 139,93                              → 140,94
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import AppUserSessionLocal, SessionLocal
from app.integrations.storage import get_storage_client
from app.main import app
from app.modules.financeiro.services.fases import sincronizar_fases
from app.modules.orcamento.services.orcamentos import update_status
from tests.conftest import SeededUser
from tests.test_portal_orcamento import ASSINATURA, FakeStorage

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"
CNPJ_OUTRO = "11444777000161"
FUNDACOES = Decimal("344.79")
ESTRUTURA = Decimal("140.94")


@pytest.fixture
def fake_storage() -> Iterator[FakeStorage]:
    storage = FakeStorage()
    app.dependency_overrides[get_storage_client] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_client, None)


# --------------------------------------------------------------------------- #
# Helpers (tudo pela API, como o usuário faz)
# --------------------------------------------------------------------------- #
def _obra_e_orcamento(
    client: TestClient,
    owner: SeededUser,
    *,
    cnpj: str = CNPJ_VALIDO,
    codigo_obra: str = "OBR-1",
) -> tuple[str, str, str]:
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": cnpj, "nome": "Cliente"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": codigo_obra, "nome": "Obra"},
    ).json()
    orc = client.post(
        f"/api/v1/obras/{obra['id']}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orçamento"},
    ).json()
    return str(obra["id"]), str(orc["id"]), str(orc["versao"]["id"])


def _bulk(client: TestClient, owner: SeededUser, vid: str, itens: list[dict[str, Any]]) -> dict:
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": itens},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()  # type: ignore[no-any-return]


def _id_por_descricao(tree: dict, descricao: str) -> str:
    return str(next(i["id"] for i in tree["itens"] if i["descricao"] == descricao))


def _folha(parent: str, desc: str, qtd: str, preco: str) -> dict[str, Any]:
    return {
        "tipo": "I",
        "parent_id": parent,
        "descricao": desc,
        "quantidade": qtd,
        "preco_unitario": preco,
    }


_RUIDO = {"quantidade": "4", "preco_unitario": "250.00"}


def _monta_duas_fases(
    client: TestClient, owner: SeededUser, vid: str, *, cod_a: str | None, cod_b: str | None
) -> None:
    """Fundações (344,79) e Estrutura (140,94), com os códigos pedidos."""
    tree = _bulk(
        client,
        owner,
        vid,
        [
            # quantidade/preço em nó não-folha: o BudgetCalculator os ignora, e
            # valor_orcado também (D3-b).
            {"tipo": "F", "codigo": cod_a, "descricao": "Fundações", **_RUIDO},
            {"tipo": "F", "codigo": cod_b, "descricao": "Estrutura", **_RUIDO},
        ],
    )
    fa, fb = _id_por_descricao(tree, "Fundações"), _id_por_descricao(tree, "Estrutura")
    tree = _bulk(
        client,
        owner,
        vid,
        [
            {"tipo": "S", "parent_id": fa, "descricao": "Sapata", **_RUIDO},
            {"tipo": "S", "parent_id": fa, "descricao": "Viga baldrame", **_RUIDO},
            {"tipo": "S", "parent_id": fb, "descricao": "Pilares", **_RUIDO},
        ],
    )
    sapata = _id_por_descricao(tree, "Sapata")
    baldrame = _id_por_descricao(tree, "Viga baldrame")
    pilares = _id_por_descricao(tree, "Pilares")
    _bulk(
        client,
        owner,
        vid,
        [
            _folha(sapata, "Concreto", "3.5", "12.34"),
            _folha(sapata, "Aço", "2", "100.55"),
            _folha(baldrame, "Forma", "1.25", "80.40"),
            _folha(pilares, "Arredondamento", "3", "0.335"),
            _folha(pilares, "Madeira", "7", "19.99"),
        ],
    )


def _aguardando(client: TestClient, owner: SeededUser, orc_id: str) -> None:
    resp = client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aguardando_aprovacao"},
    )
    assert resp.status_code == 200, resp.text


def _aprovar_pelo_painel(client: TestClient, owner: SeededUser, orc_id: str):  # type: ignore[no-untyped-def]
    return client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aprovado"},
    )


def _aprovar_pelo_portal(client: TestClient, owner: SeededUser, obra_id: str):  # type: ignore[no-untyped-def]
    resp = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    return client.post(
        f"/api/v1/portal/orcamentos/{token}/aprovar",
        json={"comentario": "De acordo.", "assinado_por": "João Cliente", "assinatura": ASSINATURA},
    )


def _fases(obra_id: str) -> dict[str, dict[str, Any]]:
    """obra_fase da obra por código (leitura de verificação, role de teste)."""
    with SessionLocal() as s:
        rows = (
            s.execute(
                text(
                    "SELECT id, codigo, descricao, valor_orcado, sort_order, ativa, "
                    "       orcamento_versao_id FROM obra_fase WHERE obra_id = :o"
                ),
                {"o": obra_id},
            )
            .mappings()
            .all()
        )
    return {r["codigo"]: dict(r) for r in rows}


def _status(orc_id: str) -> str:
    with SessionLocal() as s:
        return str(
            s.execute(
                text("SELECT status FROM orcamento WHERE id = :i"), {"i": orc_id}
            ).scalar_one()
        )


def _versao_locked(vid: str) -> bool:
    with SessionLocal() as s:
        return bool(
            s.execute(
                text("SELECT is_locked FROM orcamento_versao WHERE id = :i"), {"i": vid}
            ).scalar_one()
        )


def _cenario_aprovavel(
    client: TestClient,
    owner: SeededUser,
    *,
    cod_a: str | None = "FUN",
    cod_b: str | None = "EST",
) -> tuple[str, str, str]:
    obra_id, orc_id, vid = _obra_e_orcamento(client, owner)
    _monta_duas_fases(client, owner, vid, cod_a=cod_a, cod_b=cod_b)
    _aguardando(client, owner, orc_id)
    return obra_id, orc_id, vid


# --------------------------------------------------------------------------- #
# Aprovação pelas duas rotas
# --------------------------------------------------------------------------- #
def test_aprovar_pela_rota_patch_status_cria_fases_com_valor_exato(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner)
    assert _fases(obra_id) == {}  # nada antes da aprovação

    resp = _aprovar_pelo_painel(client, owner, orc_id)
    assert resp.status_code == 200, resp.text

    fases = _fases(obra_id)
    assert set(fases) == {"FUN", "EST"}
    assert fases["FUN"]["valor_orcado"] == FUNDACOES
    assert fases["EST"]["valor_orcado"] == ESTRUTURA
    assert fases["FUN"]["descricao"] == "Fundações"
    assert (fases["FUN"]["sort_order"], fases["EST"]["sort_order"]) == (0, 1)
    assert fases["FUN"]["ativa"] is True and fases["EST"]["ativa"] is True
    assert str(fases["FUN"]["orcamento_versao_id"]) == vid


def test_aprovar_pelo_portal_cria_fases_com_valor_exato(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner)
    assert _fases(obra_id) == {}

    resp = _aprovar_pelo_portal(client, owner, obra_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "aprovado"

    fases = _fases(obra_id)
    assert set(fases) == {"FUN", "EST"}
    assert fases["FUN"]["valor_orcado"] == FUNDACOES
    assert fases["EST"]["valor_orcado"] == ESTRUTURA
    assert str(fases["EST"]["orcamento_versao_id"]) == vid
    # a fase fica no tenant do token: company_id da obra
    with SessionLocal() as s:
        cids = s.execute(
            text("SELECT DISTINCT company_id FROM obra_fase WHERE obra_id = :o"), {"o": obra_id}
        ).all()
    assert [str(c[0]) for c in cids] == [owner.company_id]


# --------------------------------------------------------------------------- #
# Código sintético
# --------------------------------------------------------------------------- #
def test_fase_sem_codigo_recebe_codigo_sintetico(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner, cod_a=None, cod_b=None)

    resp = _aprovar_pelo_painel(client, owner, orc_id)
    assert resp.status_code == 200, resp.text

    fases = _fases(obra_id)
    assert set(fases) == {"F000", "F001"}
    assert fases["F000"]["descricao"] == "Fundações"
    assert fases["F000"]["valor_orcado"] == FUNDACOES
    assert fases["F001"]["descricao"] == "Estrutura"
    assert fases["F001"]["valor_orcado"] == ESTRUTURA


# --------------------------------------------------------------------------- #
# Duplicata de código na mesma versão → recusa a aprovação
# --------------------------------------------------------------------------- #
def _cenario_duplicado(
    client: TestClient, owner: SeededUser, *, cod_a: str | None, cod_b: str | None
) -> tuple[str, str, str]:
    """Orçamento em aguardando_aprovacao COM código duplicado. A ida para
    aguardando já recusa (D1), então a duplicata entra por SQL depois — é o
    estado que sobra de um orçamento que já estava aguardando antes do D1."""
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner, cod_a="AAA", cod_b="BBB")
    with SessionLocal() as s:
        for antigo, novo in (("AAA", cod_a), ("BBB", cod_b)):
            s.execute(
                text("UPDATE orcamento_item SET codigo = :n WHERE versao_id = :v AND codigo = :a"),
                {"n": novo, "v": vid, "a": antigo},
            )
        s.commit()
    return obra_id, orc_id, vid


def _assert_nada_mudou(obra_id: str, orc_id: str, vid: str, status_esperado: str) -> None:
    assert _fases(obra_id) == {}
    assert _status(orc_id) == status_esperado
    assert _versao_locked(vid) is False


def test_codigo_duplicado_recusa_aprovacao_pelo_painel_com_422(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_duplicado(client, owner, cod_a="DUP", cod_b="DUP")

    resp = _aprovar_pelo_painel(client, owner, orc_id)

    assert resp.status_code == 422, resp.text
    detalhe = resp.json()["detail"]
    detalhe = detalhe if isinstance(detalhe, str) else str(detalhe)
    assert "DUP" in detalhe and "Fundações" in detalhe and "Estrutura" in detalhe
    _assert_nada_mudou(obra_id, orc_id, vid, "aguardando_aprovacao")


def test_codigo_duplicado_recusa_aprovacao_pelo_portal_com_422(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_duplicado(client, owner, cod_a="DUP", cod_b="DUP")

    resp = _aprovar_pelo_portal(client, owner, obra_id)

    assert resp.status_code == 422, resp.text
    detalhe = str(resp.json()["detail"])
    assert "Fundações" in detalhe and "Estrutura" in detalhe
    _assert_nada_mudou(obra_id, orc_id, vid, "aguardando_aprovacao")
    with SessionLocal() as s:  # a evidência da decisão também foi desfeita
        n = s.execute(
            text("SELECT count(*) FROM orcamento_aprovacao WHERE orcamento_id = :o"),
            {"o": orc_id},
        ).scalar_one()
    assert n == 0


def test_codigo_sintetico_colidindo_com_codigo_explicito_recusa_com_422(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    # A 2ª fase (sort_order 1) vira "F001", igual ao código explícito da 1ª.
    obra_id, orc_id, vid = _cenario_duplicado(client, owner, cod_a="F001", cod_b=None)

    resp = _aprovar_pelo_painel(client, owner, orc_id)

    assert resp.status_code == 422, resp.text
    detalhe = str(resp.json()["detail"])
    assert "Fundações" in detalhe and "Estrutura" in detalhe
    _assert_nada_mudou(obra_id, orc_id, vid, "aguardando_aprovacao")


# --------------------------------------------------------------------------- #
# Reconciliação da segunda versão (RN-F03) — versão 2 montada por SQL (ESPEC §4.5)
# --------------------------------------------------------------------------- #
def _cria_versao_2(
    orc_id: str,
    company_id: str,
    fases: list[tuple[str | None, str, str, str, int]],
    numero: int = 2,
) -> str:
    """Insere a versão `numero` (fase, serviço, insumo por fase), bumpa `versao_atual`.
    `fases`: (codigo, descricao, quantidade, preco_unitario, sort_order)."""
    with SessionLocal() as s:
        vid2 = s.execute(
            text(
                "INSERT INTO orcamento_versao (company_id, orcamento_id, numero) "
                "VALUES (:c, :o, :n) RETURNING id"
            ),
            {"c": company_id, "o": orc_id, "n": numero},
        ).scalar_one()
        for codigo, desc, qtd, preco, ordem in fases:
            ins = text(
                "INSERT INTO orcamento_item "
                "(company_id, versao_id, parent_id, tipo, codigo, descricao, quantidade, "
                " preco_unitario, sort_order) "
                "VALUES (:c, :v, :p, :t, :cod, :d, :q, :pr, :so) RETURNING id"
            )
            base = {"c": company_id, "v": vid2, "cod": None, "q": 0, "pr": 0, "so": 0}
            fase = s.execute(
                ins, {**base, "p": None, "t": "F", "cod": codigo, "d": desc, "so": ordem}
            ).scalar_one()
            serv = s.execute(ins, {**base, "p": fase, "t": "S", "d": f"Serv {desc}"}).scalar_one()
            s.execute(ins, {**base, "p": serv, "t": "I", "d": f"Ins {desc}", "q": qtd, "pr": preco})
        s.execute(
            text("UPDATE orcamento SET versao_atual = :n WHERE id = :o"),
            {"o": orc_id, "n": numero},
        )
        s.commit()
    return str(vid2)


def _sincroniza_como_app_user(company_id: str, orc_id: str) -> None:
    """Chama o service como `get_db` faria: sessão app_user + GUC do tenant."""
    session = AppUserSessionLocal()
    try:
        session.execute(text("SELECT set_config('app.company_id', :c, true)"), {"c": company_id})
        sincronizar_fases(session, uuid.UUID(orc_id))
        session.commit()
    finally:
        session.close()


def test_segunda_versao_reconcilia_por_codigo_mantendo_id(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid1 = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc_id).status_code == 200
    antes = _fases(obra_id)
    assert set(antes) == {"FUN", "EST"}
    assert antes["FUN"]["valor_orcado"] == FUNDACOES

    # v2: FUN renomeada e re-precificada (5 × 21,37 = 106,85); EST ausente; HID nova
    # (2,5 × 33,33 = 83,325 → 83,33).
    vid2 = _cria_versao_2(
        orc_id,
        owner.company_id,
        [
            ("FUN", "Fundações revisadas", "5", "21.37", 0),
            ("HID", "Hidráulica", "2.5", "33.33", 1),
        ],
    )
    _sincroniza_como_app_user(owner.company_id, orc_id)

    depois = _fases(obra_id)
    assert set(depois) == {"FUN", "EST", "HID"}

    # mesmo código → MESMO id, descrição e valor atualizados
    assert depois["FUN"]["id"] == antes["FUN"]["id"]
    assert depois["FUN"]["descricao"] == "Fundações revisadas"
    assert depois["FUN"]["valor_orcado"] == Decimal("106.85")
    assert depois["FUN"]["ativa"] is True
    assert str(depois["FUN"]["orcamento_versao_id"]) == vid2

    # código que sumiu → inativa, linha preservada com o mesmo id e valor antigo
    assert depois["EST"]["id"] == antes["EST"]["id"]
    assert depois["EST"]["ativa"] is False
    assert depois["EST"]["valor_orcado"] == ESTRUTURA

    # código novo → fase nova, ativa
    assert depois["HID"]["id"] not in {antes["FUN"]["id"], antes["EST"]["id"]}
    assert depois["HID"]["descricao"] == "Hidráulica"
    assert depois["HID"]["valor_orcado"] == Decimal("83.33")
    assert depois["HID"]["ativa"] is True
    assert depois["HID"]["sort_order"] == 1


def test_fase_inativa_volta_a_ativa_quando_o_codigo_reaparece(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc_id).status_code == 200
    id_est = _fases(obra_id)["EST"]["id"]

    _cria_versao_2(orc_id, owner.company_id, [("FUN", "Fundações", "1", "10.00", 0)])
    _sincroniza_como_app_user(owner.company_id, orc_id)
    assert _fases(obra_id)["EST"]["ativa"] is False
    assert _fases(obra_id)["EST"]["sort_order"] == 1

    # v3 (numero = 3, v2 preservada) traz EST de volta em outra posição.
    _cria_versao_2(orc_id, owner.company_id, [("EST", "Estrutura", "2", "50.00", 7)], numero=3)
    _sincroniza_como_app_user(owner.company_id, orc_id)

    est = _fases(obra_id)["EST"]
    assert est["id"] == id_est
    assert est["ativa"] is True
    assert est["valor_orcado"] == Decimal("100.00")
    assert est["sort_order"] == 7  # D3-c: o upsert atualiza a ordem
    assert _fases(obra_id)["FUN"]["ativa"] is False


# --------------------------------------------------------------------------- #
# D3-a — a inativação é por obra
# --------------------------------------------------------------------------- #
def test_sincronizar_uma_obra_nao_toca_nas_fases_de_outra_obra_do_tenant(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra1, orc1, _ = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc1).status_code == 200

    obra2, orc2, vid2 = _obra_e_orcamento(client, owner, cnpj=CNPJ_OUTRO, codigo_obra="OBR-2")
    _monta_duas_fases(client, owner, vid2, cod_a="FUN", cod_b="EST")
    _aguardando(client, owner, orc2)
    assert _aprovar_pelo_painel(client, owner, orc2).status_code == 200
    intacta = _fases(obra2)
    assert set(intacta) == {"FUN", "EST"}

    # v2 da obra 1 sem EST: inativa EST só na obra 1.
    _cria_versao_2(orc1, owner.company_id, [("FUN", "Fundações", "1", "10.00", 0)])
    _sincroniza_como_app_user(owner.company_id, orc1)

    assert _fases(obra1)["EST"]["ativa"] is False
    assert _fases(obra2) == intacta
    assert _fases(obra2)["EST"]["ativa"] is True


# --------------------------------------------------------------------------- #
# D3-e — arredonda por folha, não no agregado
# --------------------------------------------------------------------------- #
def test_valor_orcado_arredonda_por_folha_nao_no_agregado(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _obra_e_orcamento(client, owner)
    tree = _bulk(client, owner, vid, [{"tipo": "F", "codigo": "ARR", "descricao": "Arredonda"}])
    fase = _id_por_descricao(tree, "Arredonda")
    tree = _bulk(client, owner, vid, [{"tipo": "S", "parent_id": fase, "descricao": "Serv"}])
    serv = _id_por_descricao(tree, "Serv")
    _bulk(
        client,
        owner,
        vid,
        [
            _folha(serv, "Meio centavo A", "1", "0.005"),
            _folha(serv, "Meio centavo B", "1", "0.005"),
        ],
    )
    _aguardando(client, owner, orc_id)

    assert _aprovar_pelo_painel(client, owner, orc_id).status_code == 200

    # por folha: 0,01 + 0,01 = 0,02 (no agregado seria 0,01)
    assert _fases(obra_id)["ARR"]["valor_orcado"] == Decimal("0.02")


# --------------------------------------------------------------------------- #
# D3-d — rejeitar não sincroniza
# --------------------------------------------------------------------------- #
def test_rejeitar_pelo_painel_nao_cria_fases(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner)

    resp = client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "rejeitado"},
    )

    assert resp.status_code == 200, resp.text
    assert _status(orc_id) == "rejeitado"
    assert _fases(obra_id) == {}


def test_rejeitar_pelo_portal_nao_cria_fases(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner)
    token = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header).json()[
        "token"
    ]

    resp = client.post(
        f"/api/v1/portal/orcamentos/{token}/rejeitar",
        json={"comentario": "Caro.", "assinado_por": "João Cliente", "assinatura": ASSINATURA},
    )

    assert resp.status_code == 200, resp.text
    assert _status(orc_id) == "rejeitado"
    assert _fases(obra_id) == {}


# --------------------------------------------------------------------------- #
# E-07 — um orçamento aprovado por obra
# --------------------------------------------------------------------------- #
def _segundo_orcamento_aguardando(
    client: TestClient, owner: SeededUser, obra_id: str
) -> tuple[str, str]:
    orc = client.post(
        f"/api/v1/obras/{obra_id}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orçamento 2"},
    ).json()
    orc_id, vid = str(orc["id"]), str(orc["versao"]["id"])
    _monta_duas_fases(client, owner, vid, cod_a="OUT", cod_b="TRO")
    _aguardando(client, owner, orc_id)
    return orc_id, vid


def _n_aprovacoes(orc_id: str) -> int:
    with SessionLocal() as s:
        return int(
            s.execute(
                text("SELECT count(*) FROM orcamento_aprovacao WHERE orcamento_id = :o"),
                {"o": orc_id},
            ).scalar_one()
        )


def test_aprovar_segundo_orcamento_da_obra_pelo_painel_da_409_e_nada_muda(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, vid1 = _cenario_aprovavel(client, owner)
    # orc2 vai a aguardando ANTES de orc1 ser aprovado: depois, a ida é 409 (E-07).
    orc2, vid2 = _segundo_orcamento_aguardando(client, owner, obra_id)
    assert _aprovar_pelo_painel(client, owner, orc1).status_code == 200
    fases_antes = _fases(obra_id)

    resp = _aprovar_pelo_painel(client, owner, orc2)

    assert resp.status_code == 409, resp.text
    assert "já tem um orçamento aprovado" in str(resp.json()["detail"])
    assert _status(orc2) == "aguardando_aprovacao"
    assert _versao_locked(vid2) is False
    assert _status(orc1) == "aprovado" and _versao_locked(vid1) is True
    assert _fases(obra_id) == fases_antes


def test_aprovar_segundo_orcamento_da_obra_pelo_portal_da_409_sem_gravar_assinatura(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    orc2, vid2 = _segundo_orcamento_aguardando(client, owner, obra_id)
    assert _aprovar_pelo_painel(client, owner, orc1).status_code == 200
    fases_antes = _fases(obra_id)

    resp = _aprovar_pelo_portal(client, owner, obra_id)

    assert resp.status_code == 409, resp.text
    assert fake_storage.objects == {}  # D2: recusa nunca grava a assinatura
    assert _status(orc2) == "aguardando_aprovacao"
    assert _versao_locked(vid2) is False
    assert _n_aprovacoes(orc2) == 0
    assert _fases(obra_id) == fases_antes


def test_duplicidade_no_portal_nao_grava_assinatura(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_duplicado(client, owner, cod_a="DUP", cod_b="DUP")

    resp = _aprovar_pelo_portal(client, owner, obra_id)

    assert resp.status_code == 422, resp.text
    assert fake_storage.objects == {}


def test_aprovado_para_aprovado_e_noop_e_nao_ressincroniza(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc_id).status_code == 200
    with SessionLocal() as s:  # marca o estado: se ressincronizar, a marca some
        s.execute(
            text("UPDATE obra_fase SET descricao = 'MARCA' WHERE obra_id = :o AND codigo = 'FUN'"),
            {"o": obra_id},
        )
        s.commit()

    resp = _aprovar_pelo_painel(client, owner, orc_id)

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "aprovado"
    assert _fases(obra_id)["FUN"]["descricao"] == "MARCA"
    assert _status(orc_id) == "aprovado" and _versao_locked(vid) is True


# --------------------------------------------------------------------------- #
# D1 — duplicidade barrada já em aguardando_aprovacao (painel); D4 — só aprovado
# --------------------------------------------------------------------------- #
def test_codigo_duplicado_recusa_aguardando_aprovacao_com_422(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _obra_e_orcamento(client, owner)
    _monta_duas_fases(client, owner, vid, cod_a="DUP", cod_b="DUP")

    resp = client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aguardando_aprovacao"},
    )

    assert resp.status_code == 422, resp.text
    detalhe = str(resp.json()["detail"])
    assert "DUP" in detalhe and "Fundações" in detalhe and "Estrutura" in detalhe
    assert _status(orc_id) == "rascunho"


def test_codigo_sintetico_colidindo_recusa_aguardando_aprovacao_com_422(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _obra_e_orcamento(client, owner)
    _monta_duas_fases(client, owner, vid, cod_a="F001", cod_b=None)

    resp = client.patch(
        f"/api/v1/orcamentos/{orc_id}/status",
        headers=owner.auth_header,
        json={"status": "aguardando_aprovacao"},
    )

    assert resp.status_code == 422, resp.text
    assert _status(orc_id) == "rascunho"


def test_sincronizar_orcamento_nao_aprovado_da_409(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner)  # aguardando_aprovacao

    with pytest.raises(HTTPException) as exc:
        _sincroniza_como_app_user(owner.company_id, orc_id)

    assert exc.value.status_code == 409
    assert _fases(obra_id) == {}


# --------------------------------------------------------------------------- #
# E-07 (ciclo 2) — soft-delete do aprovado, ida a aguardando, positivos
# --------------------------------------------------------------------------- #
def _patch_status(client: TestClient, owner: SeededUser, orc_id: str, novo: str):  # type: ignore[no-untyped-def]
    return client.patch(
        f"/api/v1/orcamentos/{orc_id}/status", headers=owner.auth_header, json={"status": novo}
    )


def _deleted_at_nulo(orc_id: str) -> bool:
    with SessionLocal() as s:
        return bool(
            s.execute(
                text("SELECT deleted_at IS NULL FROM orcamento WHERE id = :i"), {"i": orc_id}
            ).scalar_one()
        )


def test_excluir_orcamento_aprovado_da_409_e_nada_muda(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc_id).status_code == 200
    fases_antes = _fases(obra_id)

    resp = client.delete(f"/api/v1/orcamentos/{orc_id}", headers=owner.auth_header)

    assert resp.status_code == 409, resp.text
    assert "não pode ser excluído" in str(resp.json()["detail"])
    assert _deleted_at_nulo(orc_id)
    assert _status(orc_id) == "aprovado" and _versao_locked(vid) is True
    assert _fases(obra_id) == fases_antes


def test_excluir_orcamento_nao_aprovado_continua_funcionando(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, _ = _cenario_aprovavel(client, owner)  # aguardando_aprovacao

    resp = client.delete(f"/api/v1/orcamentos/{orc_id}", headers=owner.auth_header)

    assert resp.status_code == 204, resp.text
    assert not _deleted_at_nulo(orc_id)
    # orçamento já excluído (ou inexistente) segue 404
    resp = client.delete(f"/api/v1/orcamentos/{orc_id}", headers=owner.auth_header)
    assert resp.status_code == 404, resp.text


def test_ida_para_aguardando_com_outro_orcamento_aprovado_da_409(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    assert _aprovar_pelo_painel(client, owner, orc1).status_code == 200
    orc2 = client.post(
        f"/api/v1/obras/{obra_id}/orcamentos", headers=owner.auth_header, json={"titulo": "O2"}
    ).json()
    _monta_duas_fases(client, owner, str(orc2["versao"]["id"]), cod_a="OUT", cod_b="TRO")

    resp = _patch_status(client, owner, str(orc2["id"]), "aguardando_aprovacao")

    assert resp.status_code == 409, resp.text
    assert "já tem um orçamento aprovado" in str(resp.json()["detail"])
    assert _status(str(orc2["id"])) == "rascunho"


def test_aprovar_segundo_com_primeiro_rejeitado_funciona(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    orc2, _ = _segundo_orcamento_aguardando(client, owner, obra_id)
    assert _patch_status(client, owner, orc1, "rejeitado").status_code == 200

    resp = _aprovar_pelo_painel(client, owner, orc2)

    assert resp.status_code == 200, resp.text
    assert _status(orc2) == "aprovado" and _status(orc1) == "rejeitado"
    assert set(_fases(obra_id)) == {"OUT", "TRO"}


def test_aprovar_segundo_com_primeiro_aguardando_funciona(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)  # orc1 fica aguardando
    # a ida de orc2 a aguardando é permitida: orc1 ainda não está aprovado
    orc2, _ = _segundo_orcamento_aguardando(client, owner, obra_id)

    resp = _aprovar_pelo_painel(client, owner, orc2)

    assert resp.status_code == 200, resp.text
    assert _status(orc2) == "aprovado" and _status(orc1) == "aguardando_aprovacao"
    assert set(_fases(obra_id)) == {"OUT", "TRO"}


def test_portal_rejeitar_segundo_com_primeiro_aprovado_funciona(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    # orc2 chega a aguardando pela API ANTES de orc1 ser aprovado (depois, a ida
    # seria 409): o estado "orc1 aprovado + orc2 aguardando" é legítimo e o cliente
    # tem que poder REJEITAR orc2 — a regra E-07 vale só para aprovar.
    orc2, _ = _segundo_orcamento_aguardando(client, owner, obra_id)
    assert _aprovar_pelo_painel(client, owner, orc1).status_code == 200
    token = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header).json()[
        "token"
    ]

    resp = client.post(
        f"/api/v1/portal/orcamentos/{token}/rejeitar",
        json={"comentario": "Caro.", "assinado_por": "João Cliente", "assinatura": ASSINATURA},
    )

    assert resp.status_code == 200, resp.text
    assert _status(orc2) == "rejeitado" and _status(orc1) == "aprovado"


def test_em_revisao_para_aguardando_com_codigo_duplicado_da_422(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _obra_e_orcamento(client, owner)
    _monta_duas_fases(client, owner, vid, cod_a="DUP", cod_b="DUP")
    assert _patch_status(client, owner, orc_id, "em_revisao").status_code == 200

    resp = _patch_status(client, owner, orc_id, "aguardando_aprovacao")

    assert resp.status_code == 422, resp.text
    assert "DUP" in str(resp.json()["detail"])
    assert _status(orc_id) == "em_revisao"


# --------------------------------------------------------------------------- #
# E-07 — corridas reais (determinísticas)
#
# Uma sessão `app_user` com a GUC do tenant roda o service SEM commit, segurando
# os locks (obra e/ou linha do orçamento). Uma thread chama a API e tem de ficar
# BLOQUEADA nesses locks. Só então a sessão faz commit e a thread segue e vê o
# estado já commitado. Sem lock, a thread não bloqueia (ou termina no estado errado).
# --------------------------------------------------------------------------- #
def _corrida(
    company_id: str,
    segura: Callable[[Any], object],
    concorrente: Callable[[], Any],
) -> Any:
    """Executa `segura(session)` sem commit, dispara `concorrente()` numa thread,
    exige que ela fique bloqueada, comita e devolve a resposta da thread."""
    resultado: dict[str, Any] = {}

    def alvo() -> None:
        try:
            resultado["resp"] = concorrente()
        except BaseException as exc:  # noqa: BLE001 — repassado ao teste
            resultado["erro"] = exc

    thread = threading.Thread(target=alvo, daemon=True)
    session = AppUserSessionLocal()
    try:
        session.execute(text("SELECT set_config('app.company_id', :c, true)"), {"c": company_id})
        segura(session)  # locks seguros: NÃO comita
        thread.start()
        thread.join(1.0)
        assert thread.is_alive(), "a requisição concorrente deveria estar bloqueada no lock"
        session.commit()
    finally:
        session.rollback()  # no-op após o commit; libera os locks se algo falhou
        session.close()
        thread.join(timeout=15)
    assert not thread.is_alive(), "a requisição concorrente não terminou após o commit"
    assert "erro" not in resultado, resultado.get("erro")
    return resultado["resp"]


def _ativas(obra_id: str) -> set[str]:
    return {c for c, f in _fases(obra_id).items() if f["ativa"]}


def test_corrida_painel_x_painel_orcamentos_diferentes_so_um_aprovado(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    orc2, vid2 = _segundo_orcamento_aguardando(client, owner, obra_id)

    resp = _corrida(
        owner.company_id,
        lambda s: update_status(s, orcamento_id=uuid.UUID(orc1), new_status="aprovado"),
        lambda: _aprovar_pelo_painel(client, owner, orc2),
    )

    assert resp.status_code == 409, resp.text
    assert _status(orc1) == "aprovado" and _status(orc2) == "aguardando_aprovacao"
    assert _versao_locked(vid2) is False
    assert _ativas(obra_id) == {"FUN", "EST"}


def test_corrida_painel_x_portal_orcamentos_diferentes_so_um_aprovado(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc1, _ = _cenario_aprovavel(client, owner)
    orc2, vid2 = _segundo_orcamento_aguardando(client, owner, obra_id)  # o portal vê o mais novo

    resp = _corrida(
        owner.company_id,
        lambda s: update_status(s, orcamento_id=uuid.UUID(orc1), new_status="aprovado"),
        lambda: _aprovar_pelo_portal(client, owner, obra_id),
    )

    assert resp.status_code == 409, resp.text
    assert fake_storage.objects == {}
    assert _status(orc1) == "aprovado" and _status(orc2) == "aguardando_aprovacao"
    assert _versao_locked(vid2) is False and _n_aprovacoes(orc2) == 0
    assert _ativas(obra_id) == {"FUN", "EST"}


def test_corrida_painel_aprova_x_portal_rejeita_o_mesmo_orcamento(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, vid = _cenario_aprovavel(client, owner)
    token = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header).json()[
        "token"
    ]

    resp = _corrida(
        owner.company_id,
        lambda s: update_status(s, orcamento_id=uuid.UUID(orc_id), new_status="aprovado"),
        lambda: client.post(
            f"/api/v1/portal/orcamentos/{token}/rejeitar",
            json={"comentario": "Caro.", "assinado_por": "João", "assinatura": ASSINATURA},
        ),
    )

    # o portal reler o status sob lock: já não está aguardando → 409
    assert resp.status_code == 409, resp.text
    assert _status(orc_id) == "aprovado"
    assert _versao_locked(vid) is True
    assert _ativas(obra_id) == {"FUN", "EST"}
    assert _n_aprovacoes(orc_id) == 0 and fake_storage.objects == {}
