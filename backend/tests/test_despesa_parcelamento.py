"""S-F3 — parcelamento (RN-F08, US-F08) e a regra de "nada de float" no cálculo."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

from app.modules.financeiro.services import despesas as service
from app.modules.financeiro.services.despesas import dividir_em_parcelas, somar_meses
from tests.test_despesas import (
    API,
    DESP,
    Tenant,
    _app_session,
    auditoria,
    cat_id,
    cen,  # noqa: F401  (fixture)
    http,  # noqa: F401  (fixture)
)

D = Decimal


# --------------------------------------------------------------------------- #
# Divisão em centavos
# --------------------------------------------------------------------------- #
def test_1000_em_3_da_333_33_333_33_333_34() -> None:
    assert dividir_em_parcelas(D("1000.00"), 3) == [D("333.33"), D("333.33"), D("333.34")]


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7, 10, 12, 13, 24, 120])
@pytest.mark.parametrize(
    "total",
    ["1000.00", "100.00", "99.99", "0.99", "123456789012345.67", "10.01", "0.10", "7.77", "1.20"],
)
def test_soma_exata_residuo_na_ultima_e_nenhuma_parcela_invalida(total: str, n: int) -> None:
    t = D(total)
    if t < D("0.01") * n:
        with pytest.raises(HTTPException) as exc:
            dividir_em_parcelas(t, n)
        assert exc.value.status_code == 422
        return
    p = dividir_em_parcelas(t, n)
    assert len(p) == n
    assert sum(p, D(0)) == t  # EXATO, sem tolerância
    assert all(x > 0 and x == x.quantize(D("0.01")) for x in p)
    assert len(set(p[:-1])) <= 1  # todas iguais, menos a última
    assert p[-1] >= p[0]  # o resíduo nunca é negativo


def test_arredondamento_nao_gera_ultima_parcela_negativa() -> None:
    # HALF_UP daria 0,01 x 10 = 0,10 > 0,05 e última de -0,05
    with pytest.raises(HTTPException):
        dividir_em_parcelas(D("0.05"), 10)
    assert dividir_em_parcelas(D("0.10"), 10) == [D("0.01")] * 10
    # 100/6 = 16,666...: base 16,66 (para baixo), última 16,70; soma exata
    p = dividir_em_parcelas(D("100.00"), 6)
    assert p == [D("16.66")] * 5 + [D("16.70")] and sum(p, D(0)) == D("100.00")


@pytest.mark.parametrize(
    ("base", "meses", "esperado"),
    [
        (date(2026, 1, 15), 1, date(2026, 2, 15)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),  # clamp no fim do mês
        (date(2026, 1, 31), 2, date(2026, 3, 31)),  # relativo à data original, não à anterior
        (date(2028, 1, 31), 1, date(2028, 2, 29)),  # bissexto
        (date(2026, 11, 30), 2, date(2027, 1, 30)),  # vira o ano
        (date(2026, 12, 15), 12, date(2027, 12, 15)),
        (date(2026, 5, 10), 0, date(2026, 5, 10)),
    ],
)
def test_somar_meses(base: date, meses: int, esperado: date) -> None:
    assert somar_meses(base, meses) == esperado


# --------------------------------------------------------------------------- #
# Pela API
# --------------------------------------------------------------------------- #
def parcelada(a: Tenant, cat: str, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "obra_fase_id": a.fases[1],
        "categoria_id": cat,
        "fornecedor_nome": "Madeireira Sul",
        "descricao": "Vigas",
        "valor": "1000.00",
        "data_competencia": "2026-11-03",
        "numero_parcelas": 3,
        "primeiro_vencimento": "2026-11-30",
    }
    body.update(over)
    return body


def test_parcelar_1000_em_3_soma_exata_e_herda_dados(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    mat = cat_id(http, a)
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, mat, documento_id=a.documento_id),
    )
    assert r.status_code == 201, r.text
    out = r.json()
    ps = out["parcelas"]
    assert [p["valor"] for p in ps] == ["333.33", "333.33", "333.34"]
    assert sum((D(p["valor"]) for p in ps), D(0)) == D("1000.00")
    assert [(p["parcela_num"], p["parcela_total"]) for p in ps] == [(1, 3), (2, 3), (3, 3)]
    assert {p["grupo_parcelas_id"] for p in ps} == {out["grupo_parcelas_id"]}
    # herdam obra, fase, categoria, fornecedor (CA-F08.4) e o resto do título
    for p in ps:
        assert p["obra_id"] == a.obra_id and p["obra_fase_id"] == a.fases[1]
        assert p["categoria_id"] == mat and p["fornecedor_nome"] == "Madeireira Sul"
        assert p["descricao"] == "Vigas" and p["data_competencia"] == "2026-11-03"
        assert p["documento_id"] == a.documento_id
        assert p["status"] == "prevista" and p["data_pagamento"] is None
        assert p["created_by"] == a.user_id
    # vencimentos mensais (CA-F08.1)
    assert [p["vencimento"] for p in ps] == ["2026-11-30", "2026-12-30", "2027-01-30"]
    # e a listagem da obra enxerga os 3 títulos
    lista = http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"]
    assert {x["id"] for x in lista} == {p["id"] for p in ps}


def test_vencimento_no_fim_do_mes_usa_o_ultimo_dia(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a), numero_parcelas=4, primeiro_vencimento="2026-01-31"),
    )
    assert [p["vencimento"] for p in r.json()["parcelas"]] == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]


def test_parcelas_sao_titulos_independentes(http: TestClient, cen: dict) -> None:  # noqa: F811
    """RN-F08: pagar a 2 não altera a 1, e o comprometido/realizado seguem o status."""
    a = cen["A"]
    ps = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a)),
    ).json()["parcelas"]
    r = http.post(
        f"{DESP}/{ps[1]['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"}
    )
    assert r.status_code == 200
    assert [http.get(f"{DESP}/{p['id']}", headers=a.h()).json()["status"] for p in ps] == [
        "prevista",
        "paga",
        "prevista",
    ]
    with _app_session(a.company_id) as s:
        from sqlalchemy import text

        comp, real = s.execute(
            text(
                "SELECT COALESCE(SUM(valor) FILTER (WHERE status='prevista'),0), "
                "COALESCE(SUM(valor) FILTER (WHERE status='paga'),0) FROM despesa "
                "WHERE grupo_parcelas_id = :g"
            ),
            {"g": ps[0]["grupo_parcelas_id"]},
        ).one()
    assert (comp, real) == (D("666.67"), D("333.33"))


def test_100_em_6_da_16_66_vezes_5_mais_16_70(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a), valor="100.00", numero_parcelas=6),
    )
    assert r.status_code == 201, r.text
    valores = [p["valor"] for p in r.json()["parcelas"]]
    assert valores == ["16.66"] * 5 + ["16.70"]
    assert sum((D(v) for v in valores), D(0)) == D("100.00")


@pytest.mark.parametrize(
    "over",
    [
        {"numero_parcelas": 1},
        {"numero_parcelas": 121},
        {"valor": "0"},
        {"valor": "-5.00"},
        {"valor": "0.05", "numero_parcelas": 10},  # < 1 centavo por parcela
        {"valor": "1000.001"},
    ],
)
def test_parcelamento_invalido_e_422_e_nada_e_gravado(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
    over: dict[str, Any],
) -> None:
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a), **over),
    )
    assert r.status_code == 422, r.text
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


def test_parcelamento_e_atomico(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falha na 3ª parcela: as duas primeiras não ficam (nem despesa, nem audit)."""
    a = cen["A"]
    mat = cat_id(http, a)
    original = service._inserir
    chamadas = {"n": 0}

    def quebra(*args: Any, **kw: Any) -> Any:
        chamadas["n"] += 1
        if chamadas["n"] == 3:
            raise RuntimeError("falha simulada")
        return original(*args, **kw)

    monkeypatch.setattr(service, "_inserir", quebra)
    with TestClient(http.app, raise_server_exceptions=False) as c:
        r = c.post(
            f"{API}/obras/{a.obra_id}/despesas/parcelada", headers=a.h(), json=parcelada(a, mat)
        )
    assert r.status_code == 500 and chamadas["n"] == 3
    monkeypatch.undo()
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []
    with _app_session(a.company_id) as s:
        from sqlalchemy import text

        assert (
            s.execute(
                text("SELECT count(*) FROM audit_log WHERE table_name='despesa'")
            ).scalar_one()
            == 0
        )


def test_parcelamento_recusa_referencias_ruins(http: TestClient, cen: dict) -> None:  # noqa: F811
    a, b = cen["A"], cen["B"]
    mat = cat_id(http, a)
    url = f"{API}/obras/{a.obra_id}/despesas/parcelada"
    for over in (
        {"obra_fase_id": b.fases[0]},
        {"categoria_id": cat_id(http, b)},
        {"documento_id": b.documento_id},
    ):
        assert http.post(url, headers=a.h(), json=parcelada(a, mat, **over)).status_code == 422
    # obra de outro tenant: 404
    r = http.post(
        f"{API}/obras/{b.obra_id}/despesas/parcelada", headers=a.h(), json=parcelada(a, mat)
    )
    assert r.status_code == 404
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


def test_parcelas_geram_audit_de_insert(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    ps = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a)),
    ).json()["parcelas"]
    for p in ps:
        logs = auditoria(a.company_id, p["id"])
        assert [x["action"] for x in logs] == ["INSERT"]
        assert logs[0]["after"]["parcela_num"] == p["parcela_num"]
        assert logs[0]["after"]["valor"] == D(p["valor"])


# --------------------------------------------------------------------------- #
# Nada de float no caminho de cálculo (verificação estática)
# --------------------------------------------------------------------------- #
def test_service_nao_usa_float() -> None:
    src = Path(service.__file__).read_text()
    arvore = ast.parse(src)
    achados: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name) and no.id == "float":
            achados.append(f"linha {no.lineno}: nome 'float'")
        if isinstance(no, ast.Constant) and isinstance(no.value, float):
            achados.append(f"linha {no.lineno}: literal float {no.value!r}")
        if isinstance(no, ast.Attribute) and no.attr in {"parse_float"}:
            achados.append(f"linha {no.lineno}: {no.attr}")
    assert achados == []


@pytest.mark.parametrize("campo", ["fornecedor_nome", "descricao"])
@pytest.mark.parametrize("branco", ["   ", " \t\n "])
def test_parcelada_com_texto_so_de_espacos_e_422_e_nada_e_gravado(
    http: TestClient,  # noqa: F811
    cen: dict,  # noqa: F811
    campo: str,
    branco: str,
) -> None:
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a), **{campo: branco}),
    )
    assert r.status_code == 422, r.text
    assert campo in r.text
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


def test_grupo_de_parcelas_e_uuid_v7(http: TestClient, cen: dict) -> None:  # noqa: F811
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h(),
        json=parcelada(a, cat_id(http, a)),
    )
    assert r.json()["grupo_parcelas_id"][14] == "7"  # versão do UUID
