"""S-F3 — categorias (US-F05): seed idempotente sob concorrência, desativação, papéis."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.testclient import TestClient

from app.core.db import AppUserSessionLocal
from app.modules.financeiro.services.despesas import CATEGORIAS_PADRAO, garantir_categorias_padrao
from tests.test_despesas import (
    API,
    DESP,
    Tenant,
    _app_session,
    cat_id,
    categorias,
    cen,  # noqa: F401  (fixture)
    http,  # noqa: F401  (fixture)
    lancar,
)

CAT = f"{API}/financeiro/categorias"
PADRAO = sorted(CATEGORIAS_PADRAO)


def _nomes(cli: TestClient, t: Tenant, **p: Any) -> list[str]:
    return sorted(c["nome"] for c in categorias(cli, t, **p))


def _contagem(company_id: str) -> list[str]:
    with _app_session(company_id) as s:
        return sorted(r[0] for r in s.execute(text("SELECT nome FROM categoria_financeira")).all())


def test_primeiro_acesso_cria_o_conjunto_padrao_uma_vez(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    assert _contagem(a.company_id) == []  # a migration não semeia
    assert _nomes(http, a) == PADRAO
    assert _nomes(http, a) == PADRAO  # segundo acesso não duplica
    assert _contagem(a.company_id) == PADRAO
    for c in categorias(http, a):
        assert c["ativa"] is True


def test_seed_e_por_empresa(http: TestClient, cen: dict) -> None:  # noqa: F811
    a, b = cen["A"], cen["B"]
    _nomes(http, a)
    assert _contagem(b.company_id) == []  # B ainda não acessou
    assert _nomes(http, b) == PADRAO
    assert {c["id"] for c in categorias(http, a)}.isdisjoint(c["id"] for c in categorias(http, b))


def test_seed_concorrente_de_duas_sessoes_insere_o_conjunto_uma_vez(cen: dict) -> None:  # noqa: F811
    """Duas sessões `app_user` independentes fazem o 'primeiro acesso' ao mesmo tempo.
    A primeira segura a transação aberta depois de semear; a segunda tenta no meio.
    Sem a resolução no banco, as duas inserem o conjunto e a segunda bate em
    `uq_categoria_company_nome` (500 no primeiro acesso da empresa)."""
    a = cen["A"]
    primeira_semeou = threading.Event()
    erros: list[BaseException] = []

    def acessar(
        demora: float, sinal: threading.Event | None, espera: threading.Event | None
    ) -> None:
        try:
            with AppUserSessionLocal() as s:
                s.execute(
                    text("SELECT set_config('app.company_id', :c, true)"), {"c": a.company_id}
                )
                if espera is not None:
                    assert espera.wait(5)
                garantir_categorias_padrao(s, a.company_id)
                if sinal is not None:
                    sinal.set()
                time.sleep(demora)  # mantém a transação aberta
                s.commit()
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    t1 = threading.Thread(target=acessar, args=(0.6, primeira_semeou, None))
    t2 = threading.Thread(target=acessar, args=(0.0, None, primeira_semeou))
    t1.start()
    t2.start()
    t1.join(15)
    t2.join(15)
    assert erros == []
    assert _contagem(a.company_id) == PADRAO  # o conjunto UMA vez


def test_seed_concorrente_pela_api_nao_da_500(cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    resultados: list[int] = []
    barreira = threading.Barrier(4)

    def chamar() -> None:
        with TestClient(__import__("app.main", fromlist=["app"]).app) as c:
            barreira.wait(5)
            resultados.append(c.get(CAT, headers=a.h()).status_code)

    ts = [threading.Thread(target=chamar) for _ in range(4)]
    [t.start() for t in ts]
    [t.join(20) for t in ts]
    assert resultados == [200] * 4
    assert _contagem(a.company_id) == PADRAO


def test_renomear_ou_desativar_padrao_nao_recria_no_proximo_acesso(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    assert http.patch(f"{CAT}/{mat}", headers=a.h(), json={"nome": "Materiais"}).status_code == 200
    eq = cat_id(http, a, "Equipamento")
    http.patch(f"{CAT}/{eq}", headers=a.h(), json={"ativa": False})
    assert _contagem(a.company_id) == sorted(
        ["Materiais", "Mão de obra", "Serviço de terceiro", "Equipamento", "Administrativo"]
    )
    assert "Material" not in _nomes(http, a, incluir_inativas=True)


def test_criar_renomear_e_conflito_de_nome_sem_caixa(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(CAT, headers=a.h(), json={"nome": "Seguros"})
    assert r.status_code == 201 and r.json()["ativa"] is True
    assert http.post(CAT, headers=a.h(), json={"nome": "seguros"}).status_code == 409
    assert http.post(CAT, headers=a.h(), json={"nome": "material"}).status_code == 409  # padrão
    r2 = http.patch(f"{CAT}/{r.json()['id']}", headers=a.h(), json={"nome": "MATERIAL"})
    assert r2.status_code == 409
    assert (
        http.patch(f"{CAT}/{r.json()['id']}", headers=a.h(), json={"nome": "Apólices"}).status_code
        == 200
    )
    # a mesma categoria 'renomeada' para ela mesma em outra caixa é permitida
    assert (
        http.patch(f"{CAT}/{r.json()['id']}", headers=a.h(), json={"nome": "APÓLICES"}).status_code
        == 200
    )
    # nome em branco
    assert http.post(CAT, headers=a.h(), json={"nome": ""}).status_code == 422
    assert (
        http.patch(f"{CAT}/{r.json()['id']}", headers=a.h(), json={"nome": "   "}).status_code
        == 422
    )


def test_mesmo_nome_em_empresas_diferentes_e_permitido(http: TestClient, cen: dict) -> None:  # noqa: F811
    a, b = cen["A"], cen["B"]
    assert http.post(CAT, headers=a.h(), json={"nome": "Seguros"}).status_code == 201
    assert http.post(CAT, headers=b.h(), json={"nome": "Seguros"}).status_code == 201


def test_desativada_some_do_formulario_e_continua_nos_relatorios(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
) -> None:
    a = cen["A"]
    eq = cat_id(http, a, "Equipamento")
    d = lancar(http, a, eq)
    r = http.patch(f"{CAT}/{eq}", headers=a.h(), json={"ativa": False})
    assert r.status_code == 200 and r.json()["ativa"] is False
    # some do formulário (lista padrão) e não aceita despesa nova
    assert "Equipamento" not in _nomes(http, a)
    nova = http.post(
        f"{API}/obras/{a.obra_id}/despesas",
        headers=a.h(),
        json={
            "obra_fase_id": a.fases[0],
            "categoria_id": eq,
            "fornecedor_nome": "F",
            "descricao": "x",
            "valor": "1.00",
            "data_competencia": "2026-11-01",
            "vencimento": "2026-11-30",
        },
    )
    assert nova.status_code == 422
    # continua nos relatórios: a despesa antiga mantém o nome e a categoria é listável
    assert "Equipamento" in _nomes(http, a, incluir_inativas=True)
    antiga = http.get(f"{DESP}/{d['id']}", headers=a.h()).json()
    assert antiga["categoria_nome"] == "Equipamento"
    lista = http.get(
        f"{API}/obras/{a.obra_id}/despesas", headers=a.h(), params={"categoria_id": eq}
    )
    assert [x["id"] for x in lista.json()["items"]] == [d["id"]]
    # reativar volta ao formulário
    http.patch(f"{CAT}/{eq}", headers=a.h(), json={"ativa": True})
    assert "Equipamento" in _nomes(http, a)


def test_categoria_com_despesa_nao_e_excluivel_so_desativavel(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    lancar(http, a, mat)
    # a API não expõe exclusão
    assert http.delete(f"{CAT}/{mat}", headers=a.h()).status_code == 405
    # e o banco recusa o DELETE físico (FK sem cascade), mesmo como app_user
    with _app_session(a.company_id) as s, pytest.raises(IntegrityError):
        s.execute(text("DELETE FROM categoria_financeira WHERE id = :i"), {"i": mat})
    assert http.patch(f"{CAT}/{mat}", headers=a.h(), json={"ativa": False}).status_code == 200


def test_patch_vazio_e_404_de_categoria_inexistente(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    mat = cat_id(http, a)
    antes = [c for c in categorias(http, a) if c["id"] == mat][0]
    r = http.patch(f"{CAT}/{mat}", headers=a.h(), json={})
    assert r.status_code == 200 and r.json() == antes
    assert (
        http.patch(f"{CAT}/{uuid.uuid4()}", headers=a.h(), json={"ativa": False}).status_code == 404
    )


def test_categoria_de_outro_tenant_e_404(http: TestClient, cen: dict) -> None:  # noqa: F811
    a, b = cen["A"], cen["B"]
    mat_a = cat_id(http, a)
    cat_id(http, b)
    r = http.patch(f"{CAT}/{mat_a}", headers=b.h(), json={"ativa": False})
    assert r.status_code == 404
    assert mat_a in {c["id"] for c in categorias(http, a)}  # intacta
    assert mat_a not in {c["id"] for c in categorias(http, b)}


@pytest.mark.parametrize("role", ["campo", "viewer", "ai", "orcamentista"])
def test_papeis_sem_acesso_recebem_403_em_todas_as_rotas(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
    role: str,
) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    h = a.h(role)
    assert http.get(CAT, headers=h).status_code == 403
    assert http.post(CAT, headers=h, json={"nome": "X"}).status_code == 403
    assert http.patch(f"{CAT}/{mat}", headers=h, json={"ativa": False}).status_code == 403


def test_gestor_le_mas_nao_mexe_em_categorias(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    mat = cat_id(http, a)
    assert http.get(CAT, headers=a.h("gestor")).status_code == 200
    assert http.post(CAT, headers=a.h("gestor"), json={"nome": "X"}).status_code == 403
    assert (
        http.patch(f"{CAT}/{mat}", headers=a.h("gestor"), json={"ativa": False}).status_code == 403
    )


@pytest.mark.parametrize("role", ["owner", "admin", "financeiro"])
def test_gerencia_mexe_em_categorias(http: TestClient, cen: dict, role: str) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(CAT, headers=a.h(role), json={"nome": f"Cat {role}"})
    assert r.status_code == 201
    assert (
        http.patch(f"{CAT}/{r.json()['id']}", headers=a.h(role), json={"ativa": False}).status_code
        == 200
    )


@pytest.mark.parametrize("branco", ["   ", " \t ", "\n"])
def test_post_de_categoria_com_nome_so_de_espacos_e_422(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
    branco: str,
) -> None:
    a = cen["A"]
    antes = _nomes(http, a, incluir_inativas=True)
    r = http.post(CAT, headers=a.h(), json={"nome": branco})
    assert r.status_code == 422, r.text
    assert _nomes(http, a, incluir_inativas=True) == antes  # nada gravado (nem nome "")


def test_post_de_categoria_aplica_strip_ao_nome(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(CAT, headers=a.h(), json={"nome": "  Seguros  "})
    assert r.status_code == 201 and r.json()["nome"] == "Seguros"
