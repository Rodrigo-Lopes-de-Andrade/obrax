"""Contrato da API do financeiro (S-F2): OpenAPI, tipos, extra='forbid' e papéis.

Não usa banco: o `TenantMiddleware` só decodifica o JWT, então o token é mintado
direto. As rotas são stubs 501; o que se verifica aqui é o contrato.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.security import create_access_token
from app.main import app
from app.modules.financeiro import schemas as fin_schemas

PREFIX = "/api/v1"

# ESPEC §6, linha a linha: (método, path, status de sucesso, papéis com acesso).
# O path é o do documento; `{id}` literal.
_ADM = {"owner", "admin"}
_FIN = _ADM | {"financeiro"}  # tudo, exceto aprovar medição
_LER = _FIN | {"gestor"}  # leitura de tudo
_ANA = _LER | {"orcamentista"}  # orçado x realizado e Curva S
_DESP = _FIN | {"gestor"}  # gestor cria/edita despesa, não paga

OPERATIONS: list[tuple[str, str, int, set[str]]] = [
    # 6.1 Planejamento
    ("POST", "/obras/{obra_id}/cronograma", 201, _FIN),
    ("GET", "/obras/{obra_id}/cronograma", 200, _LER),
    ("PUT", "/cronograma/{id}/alocacoes", 200, _FIN),
    ("GET", "/obras/{obra_id}/medicoes", 200, _LER),
    ("POST", "/obras/{obra_id}/medicoes", 201, _FIN),
    ("GET", "/medicoes/{id}", 200, _LER),
    ("PUT", "/medicoes/{id}/itens", 200, _FIN),
    ("POST", "/medicoes/{id}/aprovar", 200, _ADM),
    # 6.2 Financeiro
    ("GET", "/financeiro/categorias", 200, _LER),
    ("POST", "/financeiro/categorias", 201, _FIN),
    ("PATCH", "/financeiro/categorias/{id}", 200, _FIN),
    ("GET", "/obras/{obra_id}/despesas", 200, _LER),
    ("POST", "/obras/{obra_id}/despesas", 201, _DESP),
    ("GET", "/financeiro/despesas/{id}", 200, _LER),
    ("PATCH", "/financeiro/despesas/{id}", 200, _DESP),
    ("DELETE", "/financeiro/despesas/{id}", 200, _FIN),
    ("POST", "/financeiro/despesas/{id}/pagar", 200, _FIN),
    ("POST", "/financeiro/despesas/{id}/estornar", 200, _FIN),
    ("POST", "/obras/{obra_id}/despesas/parcelada", 201, _DESP),
    ("GET", "/financeiro/recebimentos", 200, _LER),
    ("POST", "/financeiro/recebimentos/{id}/receber", 200, _FIN),
    # 6.3 Análise / 6.4 Exportação
    ("GET", "/obras/{obra_id}/financeiro/orcado-realizado", 200, _ANA),
    ("GET", "/obras/{obra_id}/financeiro/curva-s", 200, _ANA),
    ("GET", "/financeiro/fluxo-caixa", 200, _LER),
    ("GET", "/obras/{obra_id}/financeiro/export.csv", 200, _LER),
]
CSV_OP = ("GET", "/obras/{obra_id}/financeiro/export.csv")
JSON_OPS = [o for o in OPERATIONS if o[:2] != CSV_OP]
ALL_ROLES = ["owner", "admin", "gestor", "orcamentista", "financeiro", "viewer", "campo", "ai"]
BODY_METHODS = {"POST", "PUT", "PATCH"}
# POST/PUT/PATCH que não têm request body (ação sem payload).
SEM_BODY = {("POST", "/financeiro/despesas/{id}/estornar")}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return app.openapi()


@pytest.fixture(scope="module")
def http() -> TestClient:
    return TestClient(app)


def _module_paths() -> set[str]:
    return {PREFIX + p for _, p, _, _ in OPERATIONS}


def _module_ops(spec: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (m.upper(), p[len(PREFIX) :])
        for p, item in spec["paths"].items()
        if p in _module_paths()
        for m in item
    ]


def _resolve(spec: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if ref is None:
        return node
    assert ref.startswith("#/components/schemas/"), ref
    return spec["components"]["schemas"][ref.rsplit("/", 1)[1]]


def _success_schema(spec: dict[str, Any], method: str, path: str, code: int) -> dict[str, Any]:
    op = spec["paths"][PREFIX + path][method.lower()]
    return op["responses"][str(code)]["content"]["application/json"]["schema"]


# --------------------------------------------------------------------------- #
# Contagem
# --------------------------------------------------------------------------- #
def test_matriz_do_teste_tem_25_operacoes_e_19_paths() -> None:
    assert len(OPERATIONS) == 25
    assert len({p for _, p, _, _ in OPERATIONS}) == 19


def test_openapi_expoe_exatamente_as_25_operacoes_em_19_paths(spec: dict[str, Any]) -> None:
    esperado = {(m, p) for m, p, _, _ in OPERATIONS}
    atual = set(_module_ops(spec))
    assert atual == esperado, f"faltam={esperado - atual} sobram={atual - esperado}"
    assert len(_module_ops(spec)) == 25
    assert len({p for _, p in _module_ops(spec)}) == 19


def test_nenhuma_rota_do_modulo_fora_da_lista(spec: dict[str, Any]) -> None:
    """Qualquer path sob os prefixos do módulo que não esteja na matriz é sobra."""
    marcadores = ("/financeiro", "/cronograma", "/medicoes", "/despesas")
    extras = [
        p for p in spec["paths"] if any(mk in p for mk in marcadores) and p not in _module_paths()
    ]
    assert extras == []


# --------------------------------------------------------------------------- #
# response_model
# --------------------------------------------------------------------------- #
def _assert_closed(spec: dict[str, Any], node: dict[str, Any], trail: str, seen: set[str]) -> None:
    """Percorre o schema: sem objeto aberto/Any, sem `number` solto."""
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[1]
        if name in seen:
            return
        seen.add(name)
        _assert_closed(spec, _resolve(spec, node), f"{trail}->{name}", seen)
        return
    assert node != {}, f"{trail}: schema vazio (Any)"
    assert node.get("additionalProperties") is not True, f"{trail}: additionalProperties true"
    assert node.get("type") != "number", f"{trail}: number sem formato decimal"
    if node.get("type") == "object" or "properties" in node:
        assert node.get("properties"), f"{trail}: objeto sem properties"
        assert node.get("additionalProperties") is False, f"{trail}: não é extra=forbid"
        for k, v in node["properties"].items():
            _assert_closed(spec, v, f"{trail}.{k}", seen)
    for key in ("anyOf", "oneOf", "allOf"):
        for i, sub in enumerate(node.get(key, [])):
            if sub.get("type") == "number":
                # Entrada de Decimal: o Pydantic aceita number|string-decimal.
                assert any(s.get("type") == "string" and "pattern" in s for s in node[key]), (
                    f"{trail}: number sem string decimal"
                )
                continue
            _assert_closed(spec, sub, f"{trail}.{key}[{i}]", seen)
    if node.get("type") == "array":
        _assert_closed(spec, node["items"], f"{trail}[]", seen)


@pytest.mark.parametrize(("method", "path", "code", "_roles"), JSON_OPS)
def test_operacao_json_tem_response_model_nomeado(
    spec: dict[str, Any], method: str, path: str, code: int, _roles: set[str]
) -> None:
    schema = _success_schema(spec, method, path, code)
    alvo = schema["items"] if schema.get("type") == "array" else schema
    assert alvo.get("$ref", "").startswith("#/components/schemas/"), schema
    _assert_closed(spec, alvo, f"{method} {path}", set())
    assert "501" in spec["paths"][PREFIX + path][method.lower()]["responses"]


def test_exatamente_24_operacoes_json_e_export_csv_sem_modelo(spec: dict[str, Any]) -> None:
    assert len(JSON_OPS) == 24
    op = spec["paths"][PREFIX + CSV_OP[1]]["get"]
    content = op["responses"]["200"]["content"]
    assert set(content) == {"text/csv"}
    assert "$ref" not in content["text/csv"].get("schema", {})


def test_schemas_de_request_sao_fechados_e_sem_number_solto(spec: dict[str, Any]) -> None:
    for method, path, _, _ in OPERATIONS:
        op = spec["paths"][PREFIX + path][method.lower()]
        body = op.get("requestBody")
        if body is None:
            continue
        schema = body["content"]["application/json"]["schema"]
        _assert_closed(spec, schema, f"{method} {path} body", set())


# --------------------------------------------------------------------------- #
# Dinheiro/percentual: Decimal, nunca float
# --------------------------------------------------------------------------- #
def _model_classes() -> list[type[BaseModel]]:
    return [getattr(fin_schemas, n) for n in fin_schemas.__all__]


def test_schemas_exportados_sao_modelos_extra_forbid() -> None:
    assert fin_schemas.__all__
    for cls in _model_classes():
        assert cls.model_config.get("extra") == "forbid", cls.__name__


def test_nenhum_campo_float_nos_schemas() -> None:
    def contem_float(tp: Any) -> bool:
        if tp is float:
            return True
        return any(contem_float(a) for a in getattr(tp, "__args__", ()))

    for cls in _model_classes():
        for nome, campo in cls.model_fields.items():
            assert not contem_float(campo.annotation), f"{cls.__name__}.{nome} é float"


_SAIDA_SUFIXOS = ("Out", "Page", "Detail")
_CAMPO_NUMERICO = re.compile(
    r"valor|saldo|orcado|realizad|comprometido|planejad|medido|entradas|saidas|percentual"
)


def _modelos_de_resposta() -> list[type[BaseModel]]:
    return [
        c
        for c in _model_classes()
        if c.__name__.endswith(_SAIDA_SUFIXOS)
        or c.__name__ in {"FaseOrcadoRealizado", "TotaisOrcadoRealizado", "CurvaSPonto"}
        or c.__name__ in {"FluxoCaixaPeriodo"}
    ]


def _tipos_sem_nulo(spec: dict[str, Any], node: dict[str, Any]) -> set[str]:
    node = _resolve(spec, node)
    if "anyOf" in node:
        tipos: set[str] = set()
        for sub in node["anyOf"]:
            tipos |= _tipos_sem_nulo(spec, sub)
        return tipos - {"null"}
    return {node["type"]}


def _usa_saida_decimal(campo: Any) -> bool:
    """True se o campo (ou o seu `X | None`) usa DinheiroOut/FracaoOut."""

    def tem_serializador(metadata: Any) -> bool:
        return any(type(m).__name__ == "PlainSerializer" for m in metadata)

    if tem_serializador(campo.metadata):
        return True
    return any(
        tem_serializador(getattr(a, "__metadata__", ()))
        for a in getattr(campo.annotation, "__args__", ())
    ) or tem_serializador(getattr(campo.annotation, "__metadata__", ()))


def test_dinheiro_e_percentual_sao_string_decimal_na_resposta(spec: dict[str, Any]) -> None:
    """Percorre TODOS os campos monetários/percentuais de TODOS os schemas de resposta:
    têm de ser `string` (decimal), nunca `integer`/`number`; e todo campo Decimal tem
    de usar DinheiroOut/FracaoOut (quantiza e serializa em notação fixa)."""
    schemas = spec["components"]["schemas"]
    visitados = 0
    for cls in _modelos_de_resposta():
        props = schemas[cls.__name__]["properties"]
        for nome, campo in cls.model_fields.items():
            tipos = _tipos_sem_nulo(spec, props[nome])
            eh_decimal = "Decimal" in repr(campo.annotation) or _usa_saida_decimal(campo)
            por_nome = _CAMPO_NUMERICO.search(nome) and tipos != {"boolean"}
            if eh_decimal or por_nome:
                assert tipos == {"string"}, f"{cls.__name__}.{nome}: {tipos}"
                assert _usa_saida_decimal(campo), (
                    f"{cls.__name__}.{nome}: sem DinheiroOut/FracaoOut"
                )
                visitados += 1
    assert visitados >= 30


def test_dinheiro_de_saida_e_quantizado_com_half_up_e_notacao_fixa() -> None:
    from decimal import Decimal

    from pydantic import TypeAdapter

    from app.modules.financeiro.schemas._types import DinheiroOut, FracaoOut

    din = TypeAdapter(DinheiroOut)
    assert din.dump_python(din.validate_python(Decimal("33333.336633")), mode="json") == "33333.34"
    assert din.dump_python(Decimal("1E+5"), mode="json") == "100000.00"
    assert din.dump_python(din.validate_python("0.005"), mode="json") == "0.01"
    assert din.dump_python(din.validate_python("-0.005"), mode="json") == "-0.01"
    assert din.dump_json(din.validate_python("7")) == b'"7.00"'
    fra = TypeAdapter(FracaoOut)
    assert fra.dump_python(fra.validate_python("0.33335"), mode="json") == "0.3334"
    assert fra.dump_python(Decimal("1E+0"), mode="json") == "1.0000"
    assert fra.dump_python(fra.validate_python("1.05"), mode="json") == "1.0500"


def test_resposta_com_dinheiro_nao_quantizado_nao_vira_500() -> None:
    from decimal import Decimal

    item = fin_schemas.MedicaoItemOut.model_validate(
        {
            "id": str(uuid.uuid4()),
            "obra_fase_id": str(uuid.uuid4()),
            "percentual_acumulado": Decimal("0.33335"),
            "valor_medido": Decimal("33333.336633"),
        }
    )
    dados = json.loads(item.model_dump_json())
    assert dados["valor_medido"] == "33333.34"
    assert dados["percentual_acumulado"] == "0.3334"


# Campos NOT NULL do Dicionário: opcionais nos *Update, mas `null` explícito é 422.
UPDATE_NAO_NULO = {
    "/financeiro/despesas/{id}": [
        "obra_fase_id",
        "categoria_id",
        "fornecedor_nome",
        "descricao",
        "valor",
        "data_competencia",
        "vencimento",
    ],
    "/financeiro/categorias/{id}": ["nome", "ativa"],
}


@pytest.mark.parametrize(
    ("path", "campo"), [(p, c) for p, cs in UPDATE_NAO_NULO.items() for c in cs]
)
def test_patch_com_null_em_campo_not_null_devolve_422(
    spec: dict[str, Any], http: TestClient, path: str, campo: str
) -> None:
    kwargs = _request(spec, "PATCH", path)
    kwargs["json"] = {campo: None}
    resp = http.patch(headers=_token("owner"), **kwargs)
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize(("path", "campos"), list(UPDATE_NAO_NULO.items()))
def test_patch_vazio_e_valido_e_openapi_nao_anuncia_nulo(
    spec: dict[str, Any], http: TestClient, path: str, campos: list[str]
) -> None:
    kwargs = _request(spec, "PATCH", path)
    kwargs["json"] = {}
    assert http.patch(headers=_token("owner"), **kwargs).status_code == 501
    nome = spec["paths"][PREFIX + path]["patch"]["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"].rsplit("/", 1)[1]
    props = spec["components"]["schemas"][nome]["properties"]
    for campo in campos:
        # `anyOf` sozinho é ok (Decimal aceita number|string); `null` é que não.
        tipos = [props[campo].get("type")] + [s.get("type") for s in props[campo].get("anyOf", [])]
        assert "null" not in tipos, f"{nome}.{campo} anunciado como nullable"
        assert "default" not in props[campo], f"{nome}.{campo} anuncia default"


def test_patch_despesa_documento_id_null_desvincula_e_chega_ao_501(
    spec: dict[str, Any], http: TestClient
) -> None:
    kwargs = _request(spec, "PATCH", "/financeiro/despesas/{id}")
    kwargs["json"] = {"documento_id": None}
    assert http.patch(headers=_token("owner"), **kwargs).status_code == 501
    modelo = fin_schemas.DespesaUpdate.model_validate({"documento_id": None})
    assert modelo.model_dump(exclude_unset=True) == {"documento_id": None}


def test_update_omitido_nao_aparece_em_exclude_unset() -> None:
    assert fin_schemas.DespesaUpdate.model_validate({}).model_dump(exclude_unset=True) == {}
    assert fin_schemas.CategoriaUpdate.model_validate({"ativa": False}).model_dump(
        exclude_unset=True
    ) == {"ativa": False}


def test_nenhum_create_update_aceita_null_em_campo_not_null() -> None:
    """Regra geral: dos modelos de entrada, só aceitam null os campos listados
    (nulos no Dicionário ou opcionais de payload)."""
    permitido = {
        ("DespesaCreate", "documento_id"),
        ("DespesaUpdate", "documento_id"),
        ("DespesaParceladaCreate", "documento_id"),
        ("MedicaoCreate", "observacao"),
        ("MedicaoAprovar", "vencimento"),
        ("CronogramaCreate", "numero_periodos"),
    }
    entrada = ("Create", "Update", "Put", "Pagar", "Aprovar", "Receber", "In")
    for cls in _model_classes():
        if not cls.__name__.endswith(entrada):
            continue
        for nome, campo in cls.model_fields.items():
            aceita_null = type(None) in getattr(campo.annotation, "__args__", ())
            assert not aceita_null or (cls.__name__, nome) in permitido, f"{cls.__name__}.{nome}"


def test_listagem_de_despesas_tem_de_e_ate_como_o_csv(spec: dict[str, Any]) -> None:
    def params(path: str) -> dict[str, Any]:
        op = spec["paths"][PREFIX + path]["get"]
        return {p["name"]: p for p in op["parameters"]}

    lista = params("/obras/{obra_id}/despesas")
    csv = params(CSV_OP[1])
    for nome in ("de", "ate"):
        assert nome in lista
        assert lista[nome]["in"] == "query"
        assert lista[nome]["required"] is False
        assert lista[nome]["schema"] == csv[nome]["schema"]


def test_forma_dos_schemas_aprovados_na_revisao_da_sf2() -> None:
    assert "saldo" not in fin_schemas.FluxoCaixaPeriodo.model_fields
    assert "saldo_acumulado" not in fin_schemas.FluxoCaixaPeriodo.model_fields
    assert {
        "saldo_previsto",
        "saldo_realizado",
        "saldo_previsto_acumulado",
        "saldo_realizado_acumulado",
    } <= set(fin_schemas.FluxoCaixaPeriodo.model_fields)
    rec = fin_schemas.RecebimentoOut.model_fields
    assert rec["obra_nome"].annotation is str
    assert rec["medicao_numero"].annotation is int
    desp = fin_schemas.DespesaOut.model_fields
    assert desp["fase_descricao"].annotation is str
    assert desp["categoria_nome"].annotation is str  # categoria_id é NOT NULL (§4.3)


def test_docstring_de_schema_com_percentual_diz_fracao() -> None:
    com_percentual = [c for c in _model_classes() if any("percentual" in n for n in c.model_fields)]
    assert com_percentual
    for cls in com_percentual:
        assert "fração" in (cls.__doc__ or "").lower(), cls.__name__


# --------------------------------------------------------------------------- #
# Requests: extra='forbid' -> 422 (não 501) e papéis -> 403 / 501
# --------------------------------------------------------------------------- #
def _token(role: str) -> dict[str, str]:
    tok = create_access_token(user_id=uuid.uuid4(), company_id=uuid.uuid4(), role=role).token
    return {"Authorization": f"Bearer {tok}"}


def _example(spec: dict[str, Any], node: dict[str, Any]) -> Any:
    """Valor mínimo válido (só campos obrigatórios) gerado do schema OpenAPI."""
    if "$ref" in node:
        return _example(spec, _resolve(spec, node))
    if "anyOf" in node:
        subs = [s for s in node["anyOf"] if s.get("type") not in ("null", "number")]
        return _example(spec, subs[0])
    t = node.get("type")
    if t == "object":
        props = node.get("properties", {})
        return {k: _example(spec, props[k]) for k in node.get("required", [])}
    if t == "array":
        return [_example(spec, node["items"])] * max(1, node.get("minItems", 1))
    if t == "string":
        fmt = node.get("format")
        if fmt == "uuid":
            return str(uuid.uuid4())
        if fmt == "date":
            return "2026-01-15"
        if fmt == "date-time":
            return "2026-01-15T10:00:00Z"
        if "pattern" in node:
            return "0.5"  # Decimal serializado; vale para dinheiro e fração
        if "enum" in node:
            return node["enum"][0]
        return "x"
    if t == "integer":
        return int(node.get("minimum", 1))
    if t == "boolean":
        return True
    raise AssertionError(f"tipo não tratado: {node}")


def _request(
    spec: dict[str, Any], method: str, path: str, *, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    op = spec["paths"][PREFIX + path][method.lower()]
    url = PREFIX + path
    for name in ("obra_id", "id"):
        url = url.replace("{" + name + "}", str(uuid.uuid4()))
    params = {
        p["name"]: _example(spec, p["schema"])
        for p in op.get("parameters", [])
        if p["in"] == "query" and p.get("required")
    }
    kwargs: dict[str, Any] = {"url": url, "params": params}
    body = op.get("requestBody")
    if body is not None:
        payload = _example(spec, body["content"]["application/json"]["schema"])
        if extra:
            payload = {**payload, **extra}
        kwargs["json"] = payload
    return kwargs


@pytest.mark.parametrize(("method", "path", "code", "_roles"), OPERATIONS)
def test_requisicao_valida_com_papel_autorizado_devolve_501(
    spec: dict[str, Any], http: TestClient, method: str, path: str, code: int, _roles: set[str]
) -> None:
    resp = http.request(method, headers=_token("owner"), **_request(spec, method, path))
    assert resp.status_code == 501, resp.text
    assert resp.json()["status"] == 501  # RFC 7807


@pytest.mark.parametrize(
    ("method", "path"),
    [(m, p) for m, p, _, _ in OPERATIONS if m in BODY_METHODS and (m, p) not in SEM_BODY],
)
def test_campo_desconhecido_no_body_devolve_422(
    spec: dict[str, Any], http: TestClient, method: str, path: str
) -> None:
    kwargs = _request(spec, method, path, extra={"campo_desconhecido": 1})
    resp = http.request(method, headers=_token("owner"), **kwargs)
    assert resp.status_code == 422, resp.text
    assert any(e["type"] == "extra_forbidden" for e in resp.json()["errors"]), resp.text


def test_todo_request_model_e_alcancado_por_rota_post_put_patch(spec: dict[str, Any]) -> None:
    """Os modelos de entrada (`*Create/*Update/*Put/*Pagar/*Aprovar/*Receber/*In`)
    são exatamente os usados como body (ou aninhados neles); nenhum fica sem teste."""
    usados: set[str] = set()
    for method, path, _, _ in OPERATIONS:
        body = spec["paths"][PREFIX + path][method.lower()].get("requestBody")
        if body:
            usados.add(body["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[1])
    assert len(usados) == sum(
        1 for m, p, _, _ in OPERATIONS if m in BODY_METHODS and (m, p) not in SEM_BODY
    )
    sufixos = ("Create", "Update", "Put", "Pagar", "Aprovar", "Receber", "ParceladaCreate")
    entrada = {n for n in fin_schemas.__all__ if n.endswith(sufixos)}
    assert entrada == usados
    assert {"AlocacaoIn", "MedicaoItemIn"} <= set(fin_schemas.__all__)


@pytest.mark.parametrize("campo_aninhado", ["alocacoes", "itens"])
def test_campo_desconhecido_em_item_aninhado_devolve_422(
    spec: dict[str, Any], http: TestClient, campo_aninhado: str
) -> None:
    path = "/cronograma/{id}/alocacoes" if campo_aninhado == "alocacoes" else "/medicoes/{id}/itens"
    kwargs = _request(spec, "PUT", path)
    kwargs["json"][campo_aninhado][0]["lixo"] = 1
    resp = http.put(headers=_token("owner"), **kwargs)
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("role", ALL_ROLES)
@pytest.mark.parametrize(("method", "path", "code", "roles"), OPERATIONS)
def test_matriz_de_papeis_espec_9(
    spec: dict[str, Any],
    http: TestClient,
    method: str,
    path: str,
    code: int,
    roles: set[str],
    role: str,
) -> None:
    resp = http.request(method, headers=_token(role), **_request(spec, method, path))
    assert resp.status_code == (501 if role in roles else 403), (role, resp.text)


@pytest.mark.parametrize(("method", "path", "code", "roles"), OPERATIONS)
def test_papel_sem_acesso_recebe_403_antes_da_validacao_do_body(
    spec: dict[str, Any], http: TestClient, method: str, path: str, code: int, roles: set[str]
) -> None:
    kwargs = _request(spec, method, path)
    if "json" in kwargs:
        kwargs["json"] = {"lixo": 1}
    resp = http.request(method, headers=_token("campo"), **kwargs)
    assert resp.status_code == 403, resp.text


def test_sem_token_devolve_401(spec: dict[str, Any], http: TestClient) -> None:
    resp = http.request("GET", **_request(spec, "GET", "/financeiro/categorias"))
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# Validação cruzada com o frontend (lê os .ts como texto; sem Node, sem banco)
# --------------------------------------------------------------------------- #
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "lib"


def _exemplos() -> dict[str, Any]:
    texto = (FRONTEND / "mock" / "db.ts").read_text(encoding="utf-8")
    m = re.search(
        r"//\s*<financeiro-exemplos>\s*export const FINANCEIRO_EXEMPLOS\s*=\s*(\{.*\})\s*as const;"
        r"\s*//\s*</financeiro-exemplos>",
        texto,
        re.S,
    )
    assert m, "bloco <financeiro-exemplos> não encontrado em frontend/lib/mock/db.ts"
    return json.loads(m.group(1))  # type: ignore[no-any-return]


def _chave_de_resposta(spec: dict[str, Any], method: str, path: str, code: int) -> str:
    schema = _success_schema(spec, method, path, code)
    if schema.get("type") == "array":
        return schema["items"]["$ref"].rsplit("/", 1)[1] + "[]"
    return schema["$ref"].rsplit("/", 1)[1]


def test_mock_msw_valida_contra_o_pydantic() -> None:
    exemplos = _exemplos()
    for chave, valor in exemplos.items():
        base = chave.split("#", 1)[0]  # `Schema#variante` valida contra `Schema`
        nome = base.removesuffix("[]")
        modelo = getattr(fin_schemas, nome, None)
        assert modelo is not None, f"exemplo '{chave}': não existe schema '{nome}'"
        itens = valor if base.endswith("[]") else [valor]
        assert isinstance(itens, list), f"exemplo '{chave}': esperado array"
        for i, item in enumerate(itens):
            try:
                modelo.model_validate(item)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"exemplo '{chave}'[{i}] inválido contra {nome}: {exc}")


def test_toda_operacao_json_tem_exemplo_no_mock(spec: dict[str, Any]) -> None:
    exemplos = _exemplos()
    faltando = [
        f"{m} {p} -> '{_chave_de_resposta(spec, m, p, c)}'"
        for m, p, c, _ in JSON_OPS
        if _chave_de_resposta(spec, m, p, c) not in exemplos
    ]
    assert not faltando, f"operações sem exemplo no bloco FINANCEIRO_EXEMPLOS: {faltando}"


_CALL = re.compile(
    r"\b(?:api\.(?P<m>get|post|put|patch|delete)|(?P<dl>downloadBlob))\(\s*`(?P<url>[^`]*)`"
)


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def _chamadas_do_frontend() -> set[tuple[str, str]]:
    texto = (FRONTEND / "api" / "financeiro.ts").read_text(encoding="utf-8")
    achados: set[tuple[str, str]] = set()
    for m in _CALL.finditer(texto):
        metodo = "GET" if m.group("dl") else m.group("m").upper()
        url = m.group("url").split("${qs(")[0]  # descarta a query string
        url = re.sub(r"\$\{[^}]*\}", "{}", url)
        achados.add((metodo, _norm(url)))
    return achados


def test_check_contract_frontend_x_openapi(spec: dict[str, Any]) -> None:
    """Substitui o `make check-contract`, que não existe (ERRATA E-02)."""
    front = _chamadas_do_frontend()
    api_ops = {(m, _norm(PREFIX + p)) for m, p, _, _ in OPERATIONS}
    # o OpenAPI real é a fonte: a matriz do teste tem de coincidir com ele
    real = {(m, _norm(p)) for m, p in [(m, PREFIX + p) for m, p in _module_ops(spec)]}
    assert real == api_ops
    so_front = sorted(front - real)
    so_api = sorted(real - front)
    assert not so_front and not so_api, (
        f"chamadas do frontend inexistentes no OpenAPI: {so_front}; "
        f"operações do OpenAPI sem chamada no frontend: {so_api}"
    )
    assert len(front) == 25


# Variantes que os handlers MSW montam (chave `Schema#variante`, validadas contra `Schema`).
VARIANTES_OBRIGATORIAS = {
    "MedicaoDetail#rascunho",
    "DespesaOut#cancelada",
    "DespesaOut#paga",
    "RecebimentoOut#recebido",
    "MedicaoAprovadaOut#sem_recebimento",
}


def test_mock_msw_variantes_validam_contra_o_pydantic() -> None:
    exemplos = _exemplos()
    faltando = VARIANTES_OBRIGATORIAS - set(exemplos)
    assert not faltando, f"variantes ausentes no bloco <financeiro-exemplos>: {sorted(faltando)}"
    for chave, valor in exemplos.items():
        base = chave.split("#", 1)[0]
        nome = base.removesuffix("[]")
        modelo = getattr(fin_schemas, nome, None)
        assert modelo is not None, f"exemplo '{chave}': não existe schema '{nome}'"
        itens = valor if base.endswith("[]") else [valor]
        assert isinstance(itens, list), f"exemplo '{chave}': esperado array"
        for i, item in enumerate(itens):
            try:
                modelo.model_validate(item)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"exemplo '{chave}'[{i}] inválido contra {nome}: {exc}")
    sem = exemplos["MedicaoAprovadaOut#sem_recebimento"]
    assert sem["recebimento"] is None
    assert sem["aviso"]
    assert exemplos["MedicaoDetail#rascunho"]["status"] == "rascunho"
    assert exemplos["DespesaOut#cancelada"]["status"] == "cancelada"
    assert exemplos["DespesaOut#paga"]["status"] == "paga"
    assert exemplos["RecebimentoOut#recebido"]["status"] == "recebido"
