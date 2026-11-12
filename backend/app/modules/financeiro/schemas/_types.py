"""Tipos compartilhados dos schemas do financeiro.

Convenções (Dicionário §1, RN-F10): dinheiro é `Decimal` com `NUMERIC(18,2)`;
percentual é `Decimal` com `NUMERIC(7,4)` **como fração** (0.1500 = 15%). `float`
é proibido. Pydantic v2 serializa `Decimal` como string decimal no JSON.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, PlainSerializer

_CENTAVOS = Decimal("0.01")
_QUATRO_CASAS = Decimal("0.0001")


def _quantizar(valor: Decimal, casas: Decimal) -> Decimal:
    if not valor.is_finite():
        raise ValueError("valor decimal não finito")
    with localcontext() as ctx:
        ctx.prec = 60
        return valor.quantize(casas, rounding=ROUND_HALF_UP)


def _dinheiro_out(valor: Decimal) -> Decimal:
    return _quantizar(valor, _CENTAVOS)


def _fracao_out(valor: Decimal) -> Decimal:
    return _quantizar(valor, _QUATRO_CASAS)


def _fixo(valor: Decimal) -> str:
    """Notação fixa, nunca científica ("1E+5" vira "100000.00")."""
    return f"{valor:f}"


def _nada() -> Any:
    return None


def omitido(**restricoes: Any) -> Any:
    """Campo de `*Update`: opcional, mas **não nulo**. Omitido = não mexe; `null` = 422.

    O tipo anotado é o não nulo (o OpenAPI não anuncia `nullable`). Quem lê o payload
    deve usar `model_dump(exclude_unset=True)`/`model_fields_set`; o valor padrão
    interno nunca deve ser consumido.
    """
    return Field(default_factory=_nada, **restricoes)


# Entrada: valida faixa e casas (rejeita mais de 2 casas; nunca arredonda calado).
# Saída (`*Out`): sem restrição de entrada; quantiza para 2 casas com ROUND_HALF_UP
# (ex.: 100000.01 x 0.3333 = 33333.336633 vira "33333.34") e serializa sempre em
# notação fixa com 2 casas, como string ("100000.00"), nunca "1E+5".
Dinheiro = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
DinheiroPositivo = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
# Fração entre 0 e 1 (0.25 = 25%).
Fracao = Annotated[Decimal, Field(ge=0, le=1, max_digits=7, decimal_places=4)]

DinheiroOut = Annotated[
    Decimal,
    AfterValidator(_dinheiro_out),
    PlainSerializer(lambda v: _fixo(_dinheiro_out(v)), return_type=str, when_used="always"),
]
# Fração de saída: 4 casas, notação fixa. Pode passar de 1 (ex.: 1.05 = 105%).
FracaoOut = Annotated[
    Decimal,
    AfterValidator(_fracao_out),
    PlainSerializer(lambda v: _fixo(_fracao_out(v)), return_type=str, when_used="always"),
]

DespesaStatus = Literal["prevista", "paga", "cancelada"]
MedicaoStatus = Literal["rascunho", "aprovada"]
RecebimentoStatus = Literal["previsto", "recebido"]
Periodicidade = Literal["semanal", "mensal"]
