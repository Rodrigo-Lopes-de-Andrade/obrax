"""S-F3 — despesas pela API real (US-F06, F09; RN-F02; SEC-F04/F05/F07; E-10).

Tudo pelas rotas, com JWT mintado para o usuário dono da empresa semeada (a
`TenantMiddleware` só decodifica o token; o papel vem do JWT). Cenário por SQL como
`obrax`, só para montar obra/fase/documento (não há rota para eles neste módulo).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import AppUserSessionLocal, SessionLocal
from app.core.security import create_access_token
from app.main import app

API = "/api/v1"
DESP = f"{API}/financeiro/despesas"


@dataclass
class Tenant:
    company_id: str
    user_id: str
    obra_id: str
    obra2_id: str
    fases: list[str]
    documento_id: str
    cliente_id: str

    def h(self, role: str = "owner") -> dict[str, str]:
        tok = create_access_token(
            user_id=uuid.UUID(self.user_id), company_id=uuid.UUID(self.company_id), role=role
        ).token
        return {"Authorization": f"Bearer {tok}"}


def _montar(s: Any, t: dict[str, str], label: str, cpf: str) -> Tenant:
    cid = t["company_id"]
    cliente = s.execute(
        text(
            "INSERT INTO clientes (company_id, tipo_pessoa, documento, nome) "
            "VALUES (:c, 'PF', :d, 'Cli') RETURNING id"
        ),
        {"c": cid, "d": cpf},
    ).scalar_one()
    obras = []
    for i in (1, 2):
        obras.append(
            s.execute(
                text(
                    "INSERT INTO obras (company_id, cliente_id, codigo, nome) "
                    "VALUES (:c, :cl, :cod, :n) RETURNING id"
                ),
                {"c": cid, "cl": cliente, "cod": f"OB{i}-{label}", "n": f"Obra {i} {label}"},
            ).scalar_one()
        )
    fases = [
        str(
            s.execute(
                text(
                    "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, "
                    "valor_orcado, sort_order) VALUES (:c, :o, :cod, :d, 5000, :so) RETURNING id"
                ),
                {"c": cid, "o": obras[0], "cod": f"F00{i}", "d": f"Fase {i} {label}", "so": i},
            ).scalar_one()
        )
        for i in (1, 2)
    ]
    doc = s.execute(
        text(
            "INSERT INTO documento (company_id, obra_id, nome, tipo) "
            "VALUES (:c, :o, 'nf.pdf', 'nota_fiscal') RETURNING id"
        ),
        {"c": cid, "o": obras[0]},
    ).scalar_one()
    return Tenant(
        company_id=cid,
        user_id=t["user_id"],
        obra_id=str(obras[0]),
        obra2_id=str(obras[1]),
        fases=fases,
        documento_id=str(doc),
        cliente_id=str(cliente),
    )


@pytest.fixture
def cen(two_tenants: dict) -> Iterator[dict[str, Tenant]]:
    with SessionLocal() as s:
        out = {
            "A": _montar(s, two_tenants["A"], "A", "52998224725"),
            "B": _montar(s, two_tenants["B"], "B", "39053344705"),
        }
        s.commit()
    yield out  # cleanup: cascata da company em `two_tenants`


@pytest.fixture
def http() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def categorias(http: TestClient, ten: Tenant, **params: Any) -> list[dict[str, Any]]:
    r = http.get(f"{API}/financeiro/categorias", headers=ten.h(), params=params)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def cat_id(http: TestClient, ten: Tenant, nome: str = "Material") -> str:
    return next(c["id"] for c in categorias(http, ten) if c["nome"] == nome)


def corpo(ten: Tenant, categoria: str, **over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "obra_fase_id": ten.fases[0],
        "categoria_id": categoria,
        "fornecedor_nome": "Forn Ltda",
        "descricao": "Cimento",
        "valor": "100.50",
        "data_competencia": "2026-11-01",
        "vencimento": "2026-11-30",
    }
    base.update(over)
    return base


def lancar(
    http: TestClient, ten: Tenant, categoria: str, role: str = "owner", **over: Any
) -> dict[str, Any]:
    r = http.post(
        f"{API}/obras/{ten.obra_id}/despesas",
        headers=ten.h(role),
        json=corpo(ten, categoria, **over),
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def _app_session(company_id: str) -> Any:
    s = AppUserSessionLocal()
    s.execute(text("SELECT set_config('app.company_id', :c, true)"), {"c": company_id})
    return s


def somas_fase(company_id: str, fase_id: str) -> tuple[Decimal, Decimal]:
    """(comprometido, realizado) da fase, na definição do RN-F04: comprometido = prevista,
    realizado = paga, cancelada fora dos dois. Como `app_user`, sob RLS."""
    with _app_session(company_id) as s:
        row = s.execute(
            text(
                "SELECT COALESCE(SUM(valor) FILTER (WHERE status = 'prevista'), 0), "
                "       COALESCE(SUM(valor) FILTER (WHERE status = 'paga'), 0) "
                "FROM despesa WHERE obra_fase_id = :f AND deleted_at IS NULL"
            ),
            {"f": fase_id},
        ).one()
    return Decimal(row[0]), Decimal(row[1])


def auditoria(company_id: str, despesa_id: str) -> list[dict[str, Any]]:
    """Linhas de `audit_log` da despesa, em ordem; before/after como dict (o JSON do
    snapshot é lido do banco como texto, valor monetário fica string)."""
    with _app_session(company_id) as s:
        rows = s.execute(
            text(
                "SELECT action::text, actor_id::text, before::text, after::text "
                "FROM audit_log WHERE table_name = 'despesa' AND record_id = :id "
                "ORDER BY created_at, id"
            ),
            {"id": despesa_id},
        ).all()
    return [
        {
            "action": a,
            "actor_id": actor,
            "before": json.loads(b, parse_float=Decimal) if b else None,
            "after": json.loads(af, parse_float=Decimal) if af else None,
        }
        for a, actor, b, af in rows
    ]


# --------------------------------------------------------------------------- #
# Criar e listar
# --------------------------------------------------------------------------- #
def test_despesa_criada_aparece_na_listagem_da_obra(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    criada = lancar(http, a, mat)
    assert criada["status"] == "prevista"  # CA-F06.5
    assert criada["data_pagamento"] is None
    assert criada["valor"] == "100.50"
    assert criada["obra_id"] == a.obra_id
    assert criada["fase_descricao"] == "Fase 1 A"
    assert criada["categoria_nome"] == "Material"
    assert criada["created_by"] == a.user_id
    assert criada["grupo_parcelas_id"] is None and criada["parcela_num"] is None

    r = http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h())
    assert r.status_code == 200
    assert [d["id"] for d in r.json()["items"]] == [criada["id"]]
    assert r.json()["next_cursor"] is None
    det = http.get(f"{DESP}/{criada['id']}", headers=a.h())
    assert det.status_code == 200 and det.json() == criada


def test_despesa_sem_obra_fase_id_e_422(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    body = corpo(a, cat_id(http, a))
    del body["obra_fase_id"]
    r = http.post(f"{API}/obras/{a.obra_id}/despesas", headers=a.h(), json=body)
    assert r.status_code == 422  # RN-F02
    body["obra_fase_id"] = None
    r = http.post(f"{API}/obras/{a.obra_id}/despesas", headers=a.h(), json=body)
    assert r.status_code == 422
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


@pytest.mark.parametrize("valor", ["0", "0.00", "-1.00", "-0.01", "10.001"])
def test_valor_zero_negativo_ou_com_3_casas_e_recusado(
    http: TestClient, cen: dict, valor: str
) -> None:
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas",
        headers=a.h(),
        json=corpo(a, cat_id(http, a), valor=valor),
    )
    assert r.status_code == 422
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


def test_fase_de_outra_obra_e_categoria_inexistente_sao_422(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    # a fase é da obra 1; lançar na obra 2 com ela é recusado (CA-F06.3: fases da obra)
    r = http.post(f"{API}/obras/{a.obra2_id}/despesas", headers=a.h(), json=corpo(a, mat))
    assert r.status_code == 422
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas",
        headers=a.h(),
        json=corpo(a, str(uuid.uuid4())),
    )
    assert r.status_code == 422


def test_referencias_de_outro_tenant_sao_422_e_nada_e_gravado(http: TestClient, cen: dict) -> None:
    """A lança na obra de A apontando para fase, categoria ou NF de B: 422 pela
    validação (sob RLS o item de B 'não existe') e a FK composta (E-08) segue de rede."""
    a, b = cen["A"], cen["B"]
    mat_a, mat_b = cat_id(http, a), cat_id(http, b)
    url = f"{API}/obras/{a.obra_id}/despesas"
    for over in (
        {"obra_fase_id": b.fases[0]},
        {"categoria_id": mat_b},
        {"documento_id": b.documento_id},
    ):
        r = http.post(url, headers=a.h(), json=corpo(a, mat_a, **over))
        assert r.status_code == 422, (over, r.text)
    assert http.get(url, headers=a.h()).json()["items"] == []


def test_campo_desconhecido_e_status_no_body_sao_422(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas",
        headers=a.h(),
        json=corpo(a, cat_id(http, a), status="paga"),
    )
    assert r.status_code == 422


def test_listagem_filtros_e_paginacao(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    mat, eq = cat_id(http, a), cat_id(http, a, "Equipamento")
    d1 = lancar(http, a, mat, vencimento="2026-11-05", descricao="d1")
    d2 = lancar(http, a, eq, vencimento="2026-11-10", descricao="d2", obra_fase_id=a.fases[1])
    d3 = lancar(http, a, mat, vencimento="2026-11-20", descricao="d3")
    d4 = lancar(http, a, mat, vencimento="2026-12-01", descricao="d4")
    d5 = lancar(http, a, mat, vencimento="2026-12-15", descricao="d5")
    pago = http.post(
        f"{DESP}/{d3['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-21"}
    )
    assert pago.status_code == 200
    url = f"{API}/obras/{a.obra_id}/despesas"

    def ids(**params: Any) -> list[str]:
        r = http.get(url, headers=a.h(), params=params)
        assert r.status_code == 200, r.text
        return [d["id"] for d in r.json()["items"]]

    assert ids() == [d5["id"], d4["id"], d3["id"], d2["id"], d1["id"]]  # mais nova primeiro
    assert ids(status="paga") == [d3["id"]]
    assert set(ids(status="prevista")) == {d1["id"], d2["id"], d4["id"], d5["id"]}
    assert ids(obra_fase_id=a.fases[1]) == [d2["id"]]
    assert ids(categoria_id=eq) == [d2["id"]]
    assert ids(de="2026-11-10", ate="2026-11-20") == [d3["id"], d2["id"]]  # inclusivo
    assert ids(de="2026-12-01") == [d5["id"], d4["id"]]
    assert ids(ate="2026-11-05") == [d1["id"]]
    assert (
        http.get(url, headers=a.h(), params={"de": "2026-12-01", "ate": "2026-11-01"}).status_code
        == 422
    )
    assert http.get(url, headers=a.h(), params={"cursor": "lixo"}).status_code == 422
    assert http.get(url, headers=a.h(), params={"limit": 0}).status_code == 422

    # paginação por cursor: sem repetição nem perda
    vistos: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        params: dict[str, Any] = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        pag = http.get(url, headers=a.h(), params=params).json()
        vistos += [d["id"] for d in pag["items"]]
        cursor = pag["next_cursor"]
        if cursor is None:
            break
    assert vistos == [d5["id"], d4["id"], d3["id"], d2["id"], d1["id"]]


def test_listagem_e_so_da_obra(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    lancar(http, a, cat_id(http, a))
    r = http.get(f"{API}/obras/{a.obra2_id}/despesas", headers=a.h())
    assert r.status_code == 200 and r.json()["items"] == []


# --------------------------------------------------------------------------- #
# PATCH (exclude_unset)
# --------------------------------------------------------------------------- #
def test_patch_de_descricao_preserva_documento_id_e_demais_campos(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    antes = lancar(http, a, cat_id(http, a), documento_id=a.documento_id)
    assert antes["documento_id"] == a.documento_id
    r = http.patch(f"{DESP}/{antes['id']}", headers=a.h(), json={"descricao": "Cimento CP-II"})
    assert r.status_code == 200, r.text
    depois = r.json()
    assert depois["descricao"] == "Cimento CP-II"
    assert depois["documento_id"] == a.documento_id  # NF não desvinculada em silêncio
    assert {k: v for k, v in depois.items() if k != "descricao"} == {
        k: v for k, v in antes.items() if k != "descricao"
    }
    # e o que o banco guarda confere
    with _app_session(a.company_id) as s:
        row = s.execute(
            text(
                "SELECT documento_id::text, fornecedor_nome, valor, vencimento::text, "
                "data_competencia::text, categoria_id::text, obra_fase_id::text "
                "FROM despesa WHERE id = :i"
            ),
            {"i": antes["id"]},
        ).one()
    assert row == (
        a.documento_id,
        "Forn Ltda",
        Decimal("100.50"),
        "2026-11-30",
        "2026-11-01",
        antes["categoria_id"],
        a.fases[0],
    )


def test_patch_vazio_nao_muda_nada_nem_audita(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    r = http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={})
    assert r.status_code == 200 and r.json() == d
    assert len(auditoria(a.company_id, d["id"])) == 1  # só o INSERT


def test_patch_documento_id_null_desvincula_sem_apagar_o_documento(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a), documento_id=a.documento_id)
    r = http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={"documento_id": None})
    assert r.status_code == 200 and r.json()["documento_id"] is None
    with _app_session(a.company_id) as s:  # CA-F07.3: o documento continua no GED
        assert s.execute(text("SELECT count(*) FROM documento")).scalar_one() == 1


def test_patch_altera_valor_fase_e_categoria_e_valida_referencias(
    http: TestClient, cen: dict
) -> None:
    a, b = cen["A"], cen["B"]
    mat, eq = cat_id(http, a), cat_id(http, a, "Equipamento")
    d = lancar(http, a, mat)
    r = http.patch(
        f"{DESP}/{d['id']}",
        headers=a.h(),
        json={"valor": "250.75", "obra_fase_id": a.fases[1], "categoria_id": eq},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert (out["valor"], out["obra_fase_id"], out["categoria_nome"]) == (
        "250.75",
        a.fases[1],
        "Equipamento",
    )
    assert out["fase_descricao"] == "Fase 2 A"
    for ruim in (
        {"obra_fase_id": b.fases[0]},
        {"categoria_id": cat_id(http, b)},
        {"documento_id": b.documento_id},
        {"valor": "0"},
    ):
        assert http.patch(f"{DESP}/{d['id']}", headers=a.h(), json=ruim).status_code == 422, ruim


def test_patch_nao_aceita_categoria_desativada(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    mat, eq = cat_id(http, a), cat_id(http, a, "Equipamento")
    d = lancar(http, a, mat)
    assert (
        http.patch(
            f"{API}/financeiro/categorias/{eq}", headers=a.h(), json={"ativa": False}
        ).status_code
        == 200
    )
    r = http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={"categoria_id": eq})
    assert r.status_code == 422
    # manter a categoria atual (ainda que desativada depois) não é bloqueado
    http.patch(f"{API}/financeiro/categorias/{mat}", headers=a.h(), json={"ativa": False})
    r = http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={"descricao": "ok"})
    assert r.status_code == 200


def test_patch_de_paga_so_nao_financeiro_e_cancelada_e_terminal(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    assert (
        http.patch(f"{DESP}/{d['id']}", headers=a.h("gestor"), json={"valor": "1"}).status_code
        == 422
    )
    assert (
        http.patch(f"{DESP}/{d['id']}", headers=a.h("gestor"), json={"descricao": "x"}).status_code
        == 200
    )
    http.post(f"{DESP}/{d['id']}/estornar", headers=a.h())
    http.delete(f"{DESP}/{d['id']}", headers=a.h())
    assert (
        http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={"descricao": "y"}).status_code == 422
    )


# --------------------------------------------------------------------------- #
# Pagar, estornar, cancelar (ESPEC §5)
# --------------------------------------------------------------------------- #
def test_pagar_exige_data_e_muda_o_status(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    assert http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={}).status_code == 422
    assert (
        http.post(
            f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": None}
        ).status_code
        == 422
    )
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json()["status"] == "prevista"
    r = http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["data_pagamento"], r.json()["valor"]) == (
        "paga",
        "2026-11-20",
        "100.50",  # o valor pago é o do título (CA-F09.1)
    )


def test_estornar_devolve_a_prevista_e_limpa_a_data(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    r = http.post(f"{DESP}/{d['id']}/estornar", headers=a.h())
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["data_pagamento"]) == ("prevista", None)
    with _app_session(a.company_id) as s:
        row = s.execute(
            text("SELECT status::text, data_pagamento FROM despesa WHERE id = :i"), {"i": d["id"]}
        ).one()
    assert tuple(row) == ("prevista", None)


def test_delete_cancela_e_devolve_a_despesa(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    r = http.delete(f"{DESP}/{d['id']}", headers=a.h())
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelada" and r.json()["id"] == d["id"]
    # E-10: não é soft-delete; a linha continua visível, cancelada
    got = http.get(f"{DESP}/{d['id']}", headers=a.h())
    assert got.status_code == 200 and got.json()["status"] == "cancelada"
    with _app_session(a.company_id) as s:
        assert (
            s.execute(
                text("SELECT deleted_at FROM despesa WHERE id = :i"), {"i": d["id"]}
            ).scalar_one()
            is None
        )


@pytest.mark.parametrize(
    ("preparo", "acao"),
    [
        ([], "estornar"),  # prevista -> estornar
        (["pagar"], "pagar"),  # paga -> pagar
        (["pagar"], "cancelar"),  # paga -> cancelar (estorne antes)
        (["cancelar"], "pagar"),  # cancelada é terminal
        (["cancelar"], "estornar"),
        (["cancelar"], "cancelar"),
    ],
)
def test_transicao_invalida_e_422_com_a_valida_na_mensagem(
    http: TestClient, cen: dict, preparo: list[str], acao: str
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))

    def chamar(nome: str) -> Any:
        if nome == "pagar":
            return http.post(
                f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"}
            )
        if nome == "estornar":
            return http.post(f"{DESP}/{d['id']}/estornar", headers=a.h())
        return http.delete(f"{DESP}/{d['id']}", headers=a.h())

    for p in preparo:
        assert chamar(p).status_code == 200
    antes = http.get(f"{DESP}/{d['id']}", headers=a.h()).json()
    r = chamar(acao)
    assert r.status_code == 422, r.text
    assert "transição inválida" in r.text and antes["status"] in r.text
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json() == antes  # nada mudou


def test_despesa_paga_sai_do_comprometido_e_entra_no_realizado_da_fase(
    http: TestClient, cen: dict
) -> None:
    """Prova que `pagar` tem efeito semântico, não é só um UPDATE de status: a agregação
    do RN-F04 (realizado = paga, comprometido = prevista) muda de bucket a cada ação.
    A rota de análise é da S-F9; aqui a definição é replicada sobre o banco, sob RLS."""
    a = cen["A"]
    mat = cat_id(http, a)
    fase = a.fases[0]
    d = lancar(http, a, mat, valor="100.50")
    outra = lancar(http, a, mat, valor="40.00")  # ficará prevista o tempo todo
    lancar(http, a, mat, valor="7.00", obra_fase_id=a.fases[1])
    assert somas_fase(a.company_id, fase) == (Decimal("140.50"), Decimal("0"))

    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    assert somas_fase(a.company_id, fase) == (Decimal("40.00"), Decimal("100.50"))
    assert somas_fase(a.company_id, a.fases[1]) == (
        Decimal("7.00"),
        Decimal("0"),
    )  # outra fase intacta

    http.post(f"{DESP}/{d['id']}/estornar", headers=a.h())
    assert somas_fase(a.company_id, fase) == (Decimal("140.50"), Decimal("0"))

    http.delete(f"{DESP}/{outra['id']}", headers=a.h())  # cancelada: nenhum dos dois
    assert somas_fase(a.company_id, fase) == (Decimal("100.50"), Decimal("0"))


# --------------------------------------------------------------------------- #
# Auditoria (SEC-F07, CA-F09.4)
# --------------------------------------------------------------------------- #
def test_audit_do_pagamento_e_distinguivel_de_um_patch_de_descricao(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    http.patch(f"{DESP}/{d['id']}", headers=a.h(), json={"descricao": "Nova descrição"})
    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    logs = auditoria(a.company_id, d["id"])
    assert [x["action"] for x in logs] == ["INSERT", "UPDATE", "UPDATE"]
    assert {x["actor_id"] for x in logs} == {a.user_id}  # autor (CA-F09.4)

    patch, pgto = logs[1], logs[2]
    # PATCH de descrição: muda a descrição e NÃO toca status nem data de pagamento
    assert patch["before"]["descricao"] == "Cimento"
    assert patch["after"]["descricao"] == "Nova descrição"
    assert patch["before"]["status"] == patch["after"]["status"] == "prevista"
    assert patch["after"]["data_pagamento"] is None
    # Pagamento: muda status e data de pagamento e NÃO toca a descrição
    assert (pgto["before"]["status"], pgto["after"]["status"]) == ("prevista", "paga")
    assert (pgto["before"]["data_pagamento"], pgto["after"]["data_pagamento"]) == (
        None,
        "2026-11-20",
    )
    assert pgto["before"]["descricao"] == pgto["after"]["descricao"] == "Nova descrição"
    # só o pagamento chega a 'paga': a consulta por campo separa os dois
    assert [x["action"] for x in logs if (x["after"] or {}).get("status") == "paga"] == ["UPDATE"]
    assert pgto["after"]["valor"] == Decimal("100.50")


def test_audit_de_estorno_e_cancelamento(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    http.post(f"{DESP}/{d['id']}/estornar", headers=a.h())
    http.delete(f"{DESP}/{d['id']}", headers=a.h())
    logs = auditoria(a.company_id, d["id"])
    trilha = (
        [(x["before"] or {}).get("status") for x in logs],
        [(x["after"] or {}).get("status") for x in logs],
    )
    assert trilha == (
        [None, "prevista", "paga", "prevista"],
        ["prevista", "paga", "prevista", "cancelada"],
    )
    assert logs[-1]["actor_id"] == a.user_id


def test_acao_recusada_nao_deixa_audit(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    assert http.post(f"{DESP}/{d['id']}/estornar", headers=a.h()).status_code == 422
    assert len(auditoria(a.company_id, d["id"])) == 1


# --------------------------------------------------------------------------- #
# Papéis (SEC-F05) e isolamento (SEC-F04)
# --------------------------------------------------------------------------- #
def _rotas(a: Tenant, d_id: str) -> list[tuple[str, str, dict[str, Any] | None]]:
    cat = str(uuid.uuid4())
    corpo_valido = {
        "obra_fase_id": a.fases[0],
        "categoria_id": cat,
        "fornecedor_nome": "F",
        "descricao": "d",
        "valor": "10.00",
        "data_competencia": "2026-11-01",
    }
    return [
        ("GET", f"{API}/obras/{a.obra_id}/despesas", None),
        ("POST", f"{API}/obras/{a.obra_id}/despesas", {**corpo_valido, "vencimento": "2026-11-30"}),
        (
            "POST",
            f"{API}/obras/{a.obra_id}/despesas/parcelada",
            {**corpo_valido, "numero_parcelas": 3, "primeiro_vencimento": "2026-11-30"},
        ),
        ("GET", f"{DESP}/{d_id}", None),
        ("PATCH", f"{DESP}/{d_id}", {"descricao": "x"}),
        ("DELETE", f"{DESP}/{d_id}", None),
        ("POST", f"{DESP}/{d_id}/pagar", {"data_pagamento": "2026-11-20"}),
        ("POST", f"{DESP}/{d_id}/estornar", None),
    ]


@pytest.mark.parametrize("role", ["campo", "viewer", "ai", "orcamentista"])
def test_papeis_sem_acesso_recebem_403_em_todas_as_rotas(
    http: TestClient, cen: dict, role: str
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    for metodo, url, body in _rotas(a, d["id"]):
        r = http.request(metodo, url, headers=a.h(role), json=body)
        assert r.status_code == 403, (role, metodo, url, r.status_code)
    # e nada mudou
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json() == d


def test_gestor_lanca_edita_e_parcela_mas_nao_paga_cancela_nem_estorna(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    d = lancar(http, a, mat, role="gestor")
    assert http.get(f"{DESP}/{d['id']}", headers=a.h("gestor")).status_code == 200
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h("gestor")).status_code == 200
    assert (
        http.patch(f"{DESP}/{d['id']}", headers=a.h("gestor"), json={"descricao": "g"}).status_code
        == 200
    )
    par = http.post(
        f"{API}/obras/{a.obra_id}/despesas/parcelada",
        headers=a.h("gestor"),
        json={
            "obra_fase_id": a.fases[0],
            "categoria_id": mat,
            "fornecedor_nome": "F",
            "descricao": "p",
            "valor": "90.00",
            "data_competencia": "2026-11-01",
            "numero_parcelas": 3,
            "primeiro_vencimento": "2026-11-30",
        },
    )
    assert par.status_code == 201
    r = http.post(
        f"{DESP}/{d['id']}/pagar", headers=a.h("gestor"), json={"data_pagamento": "2026-11-20"}
    )
    assert r.status_code == 403
    assert http.post(f"{DESP}/{d['id']}/estornar", headers=a.h("gestor")).status_code == 403
    assert http.delete(f"{DESP}/{d['id']}", headers=a.h("gestor")).status_code == 403
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json()["status"] == "prevista"


@pytest.mark.parametrize("role", ["owner", "admin", "financeiro"])
def test_papeis_de_gerencia_pagam_estornam_e_cancelam(
    http: TestClient, cen: dict, role: str
) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a), role=role)
    assert (
        http.post(
            f"{DESP}/{d['id']}/pagar", headers=a.h(role), json={"data_pagamento": "2026-11-20"}
        ).status_code
        == 200
    )
    assert http.post(f"{DESP}/{d['id']}/estornar", headers=a.h(role)).status_code == 200
    assert http.delete(f"{DESP}/{d['id']}", headers=a.h(role)).status_code == 200


def test_outro_tenant_recebe_404_nunca_403(http: TestClient, cen: dict) -> None:
    a, b = cen["A"], cen["B"]
    d = lancar(http, a, cat_id(http, a))
    mat_b = cat_id(http, b)
    for metodo, url, body in _rotas(a, d["id"]):
        # B (owner) nas rotas de A: obra e despesa "não existem" para B
        if body and "categoria_id" in body:
            body = {**body, "categoria_id": mat_b, "obra_fase_id": b.fases[0]}
        r = http.request(metodo, url, headers=b.h(), json=body)
        assert r.status_code == 404, (metodo, url, r.status_code, r.text)
    # e nada mudou para A
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json() == d
    assert len(auditoria(a.company_id, d["id"])) == 1
    # B não vê a despesa de A na própria listagem
    assert http.get(f"{API}/obras/{b.obra_id}/despesas", headers=b.h()).json()["items"] == []


# --------------------------------------------------------------------------- #
# Gatilho de auditoria no catálogo (E-11)
# --------------------------------------------------------------------------- #
def test_gatilho_audit_despesa_existe_no_catalogo_com_a_funcao_generica() -> None:
    with SessionLocal() as s:
        rows = s.execute(
            text(
                "SELECT t.tgname, c.relname, p.proname, t.tgenabled, pg_get_triggerdef(t.oid) "
                "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "JOIN pg_proc p ON p.oid = t.tgfoid "
                "WHERE NOT t.tgisinternal AND t.tgname IN ('audit_despesa', 'audit_documento')"
            )
        ).all()
    por_nome = {r[0]: r for r in rows}
    assert "audit_despesa" in por_nome
    nome, tabela, funcao, habilitado, definicao = por_nome["audit_despesa"]
    assert (tabela, funcao, habilitado) == ("despesa", "audit_trigger", "O")  # a mesma de documento
    assert por_nome["audit_documento"][2] == funcao
    for evento in ("INSERT", "UPDATE", "DELETE"):
        assert evento in definicao
    assert "FOR EACH ROW" in definicao


# --------------------------------------------------------------------------- #
# GET /obras/{obra_id}/fases (E-11)
# --------------------------------------------------------------------------- #
def test_fases_da_obra_ordenadas_por_codigo_com_inativa(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    with SessionLocal() as s:
        s.execute(text("UPDATE obra_fase SET ativa = false WHERE id = :i"), {"i": a.fases[1]})
        s.execute(
            text(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, "
                "sort_order) VALUES (:c, :o, 'F000', 'Primeira por código', 0, 99)"
            ),
            {"c": a.company_id, "o": a.obra_id},
        )
        s.commit()
    r = http.get(f"{API}/obras/{a.obra_id}/fases", headers=a.h())
    assert r.status_code == 200, r.text
    fases = r.json()
    assert [f["codigo"] for f in fases] == ["F000", "F001", "F002"]
    assert all(set(f) == {"id", "codigo", "descricao", "ativa"} for f in fases)
    assert [f["ativa"] for f in fases] == [True, True, False]  # inativa aparece
    assert fases[1]["id"] == a.fases[0] and fases[1]["descricao"] == "Fase 1 A"
    assert http.get(f"{API}/obras/{a.obra2_id}/fases", headers=a.h()).json() == []


def test_fases_de_obra_de_outro_tenant_e_404(http: TestClient, cen: dict) -> None:
    a, b = cen["A"], cen["B"]
    assert http.get(f"{API}/obras/{b.obra_id}/fases", headers=a.h()).status_code == 404
    assert http.get(f"{API}/obras/{uuid.uuid4()}/fases", headers=a.h()).status_code == 404
    # e o positivo equivalente: B enxerga a própria
    assert len(http.get(f"{API}/obras/{b.obra_id}/fases", headers=b.h()).json()) == 2


@pytest.mark.parametrize("role", ["campo", "viewer", "ai", "orcamentista"])
def test_fases_papeis_sem_acesso_recebem_403(http: TestClient, cen: dict, role: str) -> None:
    a = cen["A"]
    assert http.get(f"{API}/obras/{a.obra_id}/fases", headers=a.h(role)).status_code == 403


@pytest.mark.parametrize("role", ["owner", "admin", "financeiro", "gestor"])
def test_fases_papeis_de_lancamento_leem(http: TestClient, cen: dict, role: str) -> None:
    a = cen["A"]
    assert http.get(f"{API}/obras/{a.obra_id}/fases", headers=a.h(role)).status_code == 200


# --------------------------------------------------------------------------- #
# Ciclo 2: texto em branco, fase/documento de outra obra, congelamento, data futura
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("campo", ["fornecedor_nome", "descricao"])
@pytest.mark.parametrize("branco", ["   ", " \t\n "])
def test_post_com_texto_so_de_espacos_e_422_e_nada_e_gravado(
    http: TestClient, cen: dict, campo: str, branco: str
) -> None:
    a = cen["A"]
    r = http.post(
        f"{API}/obras/{a.obra_id}/despesas",
        headers=a.h(),
        json=corpo(a, cat_id(http, a), **{campo: branco}),
    )
    assert r.status_code == 422, r.text
    assert campo in r.text  # CA-F06.1
    assert http.get(f"{API}/obras/{a.obra_id}/despesas", headers=a.h()).json()["items"] == []


def test_post_aplica_strip_em_fornecedor_e_descricao(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a), fornecedor_nome="  Forn  ", descricao="  Cimento ")
    assert (d["fornecedor_nome"], d["descricao"]) == ("Forn", "Cimento")


def _fase_e_documento_da_obra2(a: Tenant) -> tuple[str, str]:
    with SessionLocal() as s:
        fase = s.execute(
            text(
                "INSERT INTO obra_fase (company_id, obra_id, codigo, descricao, valor_orcado, "
                "sort_order) VALUES (:c, :o, 'X001', 'Fase da obra 2', 100, 1) RETURNING id"
            ),
            {"c": a.company_id, "o": a.obra2_id},
        ).scalar_one()
        doc = s.execute(
            text(
                "INSERT INTO documento (company_id, obra_id, nome, tipo) "
                "VALUES (:c, :o, 'nf2.pdf', 'nota_fiscal') RETURNING id"
            ),
            {"c": a.company_id, "o": a.obra2_id},
        ).scalar_one()
        s.commit()
    return str(fase), str(doc)


def test_fase_e_documento_de_outra_obra_da_mesma_empresa_sao_422(
    http: TestClient, cen: dict
) -> None:
    a = cen["A"]
    mat = cat_id(http, a)
    fase2, doc2 = _fase_e_documento_da_obra2(a)
    d = lancar(http, a, mat, documento_id=a.documento_id)
    url = f"{DESP}/{d['id']}"
    r = http.patch(url, headers=a.h(), json={"obra_fase_id": fase2})
    assert r.status_code == 422, r.text
    r = http.patch(url, headers=a.h(), json={"documento_id": doc2})
    assert r.status_code == 422, r.text
    # no lançamento também
    post = f"{API}/obras/{a.obra_id}/despesas"
    assert http.post(post, headers=a.h(), json=corpo(a, mat, obra_fase_id=fase2)).status_code == 422
    assert http.post(post, headers=a.h(), json=corpo(a, mat, documento_id=doc2)).status_code == 422
    # nada mudou
    assert http.get(url, headers=a.h()).json() == d


_NOVOS_VALORES = {
    "valor": "1.00",
    "categoria_id": "EQUIPAMENTO",  # trocado pelo id real no teste
    "obra_fase_id": "FASE2",
    "data_competencia": "2026-10-01",
    "vencimento": "2026-12-31",
}


@pytest.mark.parametrize("campo", sorted(_NOVOS_VALORES))
def test_despesa_paga_tem_cada_campo_financeiro_congelado(
    http: TestClient, cen: dict, campo: str
) -> None:
    from app.modules.financeiro.services.despesas import _FINANCEIROS

    assert set(_NOVOS_VALORES) == set(_FINANCEIROS)  # a lista do teste acompanha o código
    a = cen["A"]
    novo = {
        "EQUIPAMENTO": cat_id(http, a, "Equipamento"),
        "FASE2": a.fases[1],
    }.get(_NOVOS_VALORES[campo], _NOVOS_VALORES[campo])
    d = lancar(http, a, cat_id(http, a))
    http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": "2026-11-20"})
    antes = http.get(f"{DESP}/{d['id']}", headers=a.h()).json()
    r = http.patch(f"{DESP}/{d['id']}", headers=a.h("gestor"), json={campo: novo})
    assert r.status_code == 422, r.text
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json() == antes
    # contraprova: em despesa prevista o mesmo PATCH passa
    p = lancar(http, a, cat_id(http, a))
    assert http.patch(f"{DESP}/{p['id']}", headers=a.h(), json={campo: novo}).status_code == 200


def test_data_de_pagamento_futura_e_422_hoje_passa(http: TestClient, cen: dict) -> None:
    a = cen["A"]
    d = lancar(http, a, cat_id(http, a))
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    amanha = (hoje + timedelta(days=1)).isoformat()
    r = http.post(f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": amanha})
    assert r.status_code == 422, r.text
    assert http.get(f"{DESP}/{d['id']}", headers=a.h()).json()["status"] == "prevista"
    assert len(auditoria(a.company_id, d["id"])) == 1
    ok = http.post(
        f"{DESP}/{d['id']}/pagar", headers=a.h(), json={"data_pagamento": hoje.isoformat()}
    )
    assert ok.status_code == 200 and ok.json()["data_pagamento"] == hoje.isoformat()
