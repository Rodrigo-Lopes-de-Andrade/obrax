"""B5.5 — importação de planilha XLSX da EAP (US-13).

Parsing e validação linha-a-linha (puro, sem DB). Template com colunas fixas;
as linhas vêm em ordem hierárquica (uma Fase, depois seus Serviços, depois os
Insumos de cada serviço). Erros são devolvidos como lista de
`{linha, campo, mensagem}` — o import é tudo-ou-nada.

`build_template()` gera o modelo para download (F5.5). Import até 5000 linhas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook

MAX_LINHAS = 5000

# Cabeçalhos do template (a 1ª linha da planilha). Comparação case-insensitive.
HEADERS = ["tipo", "codigo", "descricao", "unidade", "quantidade", "preco_unitario"]

# Aceita rótulos amigáveis além de F/S/I.
_TIPO_MAP = {
    "f": "F",
    "fase": "F",
    "s": "S",
    "servico": "S",
    "serviço": "S",
    "i": "I",
    "insumo": "I",
    "mo": "I",
    "mão de obra": "I",
    "mao de obra": "I",
}
_PAI_ESPERADO = {"F": None, "S": "F", "I": "S"}


@dataclass
class LinhaEAP:
    """Uma linha válida já normalizada (pré-inserção)."""

    tipo: str
    codigo: str | None
    descricao: str
    unidade: str | None
    quantidade: Decimal
    preco_unitario: Decimal


@dataclass
class ParseResult:
    linhas: list[LinhaEAP] = field(default_factory=list)
    erros: list[dict[str, Any]] = field(default_factory=list)


def _erro(linha: int, campo: str, mensagem: str) -> dict[str, Any]:
    return {"linha": linha, "campo": campo, "mensagem": mensagem}


def _to_decimal(raw: Any) -> Decimal:
    """Converte célula (número ou texto BR/US) em Decimal sem passar por float.
    Levanta InvalidOperation se inválido."""
    if raw is None or raw == "":
        return Decimal(0)
    if isinstance(raw, bool):  # bool é subclasse de int — rejeita explicitamente
        raise InvalidOperation
    if isinstance(raw, int):
        return Decimal(raw)
    texto = str(raw).strip()
    if isinstance(raw, float):
        # Passa pela repr do str() do próprio Python (evita "100.10000000001").
        return Decimal(texto)
    # Texto: normaliza formato pt-BR (1.234,56) e en-US (1,234.56).
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return Decimal(texto)


def parse_xlsx(content: bytes) -> ParseResult:
    """Lê e valida a planilha. Nunca levanta por conteúdo inválido — acumula em
    `erros`. Levanta ValueError só se o arquivo não for um XLSX legível."""
    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 — arquivo corrompido/não-XLSX
        raise ValueError("arquivo não é um XLSX válido") from exc

    ws = wb.active
    result = ParseResult()
    if ws is None:
        result.erros.append(_erro(0, "arquivo", "planilha vazia"))
        return result

    linhas = list(ws.iter_rows(values_only=True))
    wb.close()
    if not linhas:
        result.erros.append(_erro(0, "arquivo", "planilha vazia"))
        return result

    # Mapeia cabeçalho → índice de coluna.
    header = [str(c).strip().lower() if c is not None else "" for c in linhas[0]]
    col = {name: header.index(name) for name in HEADERS if name in header}
    for obrigatorio in ("tipo", "descricao"):
        if obrigatorio not in col:
            result.erros.append(
                _erro(1, obrigatorio, f"coluna obrigatória '{obrigatorio}' ausente no cabeçalho")
            )
    if result.erros:
        return result

    dados = linhas[1:]
    if len(dados) > MAX_LINHAS:
        result.erros.append(
            _erro(0, "arquivo", f"planilha excede {MAX_LINHAS} linhas ({len(dados)})")
        )
        return result

    def get(row: tuple[Any, ...], name: str) -> Any:
        idx = col.get(name)
        return row[idx] if idx is not None and idx < len(row) else None

    tem_fase = False
    tem_servico = False
    for offset, row in enumerate(dados):
        linha_num = offset + 2  # +1 header, +1 base-1
        if all(c is None or str(c).strip() == "" for c in row):
            continue  # linha em branco

        tipo_raw = get(row, "tipo")
        tipo = _TIPO_MAP.get(str(tipo_raw).strip().lower()) if tipo_raw is not None else None
        if tipo is None:
            result.erros.append(_erro(linha_num, "tipo", "tipo inválido (use F, S ou I)"))
            continue

        descricao_raw = get(row, "descricao")
        descricao = str(descricao_raw).strip() if descricao_raw is not None else ""
        if not descricao:
            result.erros.append(_erro(linha_num, "descricao", "descrição obrigatória"))
        elif len(descricao) > 300:
            result.erros.append(_erro(linha_num, "descricao", "descrição excede 300 caracteres"))

        # Hierarquia: o pai esperado precisa já ter aparecido acima.
        pai = _PAI_ESPERADO[tipo]
        if pai == "F" and not tem_fase:
            result.erros.append(_erro(linha_num, "tipo", "serviço sem fase anterior"))
        elif pai == "S" and not tem_servico:
            result.erros.append(_erro(linha_num, "tipo", "insumo sem serviço anterior"))

        codigo_raw = get(row, "codigo")
        codigo = str(codigo_raw).strip() if codigo_raw not in (None, "") else None
        if codigo and len(codigo) > 60:
            result.erros.append(_erro(linha_num, "codigo", "código excede 60 caracteres"))
        unidade_raw = get(row, "unidade")
        unidade = str(unidade_raw).strip() if unidade_raw not in (None, "") else None
        if unidade and len(unidade) > 20:
            result.erros.append(_erro(linha_num, "unidade", "unidade excede 20 caracteres"))

        quantidade = Decimal(0)
        preco = Decimal(0)
        try:
            quantidade = _to_decimal(get(row, "quantidade"))
            if quantidade < 0:
                result.erros.append(_erro(linha_num, "quantidade", "quantidade negativa"))
        except InvalidOperation:
            result.erros.append(_erro(linha_num, "quantidade", "quantidade não é um número"))
        try:
            preco = _to_decimal(get(row, "preco_unitario"))
            if preco < 0:
                result.erros.append(_erro(linha_num, "preco_unitario", "preço negativo"))
        except InvalidOperation:
            result.erros.append(_erro(linha_num, "preco_unitario", "preço não é um número"))

        if tipo == "F":
            tem_fase = True
            tem_servico = False
        elif tipo == "S":
            tem_servico = True

        result.linhas.append(
            LinhaEAP(
                tipo=tipo,
                codigo=codigo,
                descricao=descricao[:300],
                unidade=unidade,
                quantidade=quantidade,
                preco_unitario=preco,
            )
        )

    return result


def build_template() -> bytes:
    """Gera o modelo XLSX (cabeçalho + exemplo) para download (F5.5)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Orçamento"
    ws.append(HEADERS)
    exemplos = [
        ["F", "", "Fundações", "", "", ""],
        ["S", "", "Sapatas", "", "", ""],
        ["I", "SINAPI-000001", "Concreto usinado fck 25MPa", "m³", 12.5, 480.00],
        ["I", "SINAPI-000002", "Armadura de aço CA-50", "kg", 320, 12.30],
        ["S", "", "Vigas baldrame", "", "", ""],
        ["I", "SINAPI-000003", "Fôrma de madeira", "m²", 45, 65.00],
    ]
    for linha in exemplos:
        ws.append(linha)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
