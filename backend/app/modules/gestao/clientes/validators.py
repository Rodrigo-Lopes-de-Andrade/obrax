"""Validação de CPF (pessoa física) e CNPJ (pessoa jurídica) — B2.2.

`validate_documento` normaliza o documento para apenas dígitos e valida o
dígito verificador conforme o `tipo_pessoa`. Levanta `ValueError` em caso
inválido (convertido em 422 pelo Pydantic no schema, ou em HTTPException 422
no service durante o PATCH). O valor normalizado (só dígitos) é o que vai
para o banco — a unicidade `(company_id, documento)` compara dígitos crus.
"""

from __future__ import annotations


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _valid_cpf(digits: str) -> bool:
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for length in (9, 10):
        total = sum(int(digits[i]) * (length + 1 - i) for i in range(length))
        check = (total * 10) % 11 % 10
        if check != int(digits[length]):
            return False
    return True


def _valid_cnpj(digits: str) -> bool:
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for length, weights in ((12, weights_first), (13, [6, *weights_first])):
        total = sum(int(digits[i]) * weights[i] for i in range(length))
        rem = total % 11
        check = 0 if rem < 2 else 11 - rem
        if check != int(digits[length]):
            return False
    return True


def validate_documento(tipo_pessoa: str, documento: str) -> str:
    """Retorna o documento normalizado (só dígitos) se válido para o tipo;
    caso contrário levanta `ValueError`."""
    digits = _only_digits(documento)
    if tipo_pessoa == "PF":
        if not _valid_cpf(digits):
            raise ValueError("CPF inválido")
    elif tipo_pessoa == "PJ":
        if not _valid_cnpj(digits):
            raise ValueError("CNPJ inválido")
    else:  # pragma: no cover - tipo_pessoa é Literal['PF','PJ'] no schema
        raise ValueError("tipo_pessoa deve ser 'PF' ou 'PJ'")
    return digits
