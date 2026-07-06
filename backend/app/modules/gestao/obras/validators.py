"""Validação de regra de negócio de obras (B2.3).

`validate_date_order` garante `data_prevista_fim >= data_inicio` quando ambas
as datas estão presentes. Levanta `ValueError` em caso inválido (convertido em
422 pelo Pydantic no schema durante o POST, ou em HTTPException 422 no service
durante o PATCH — que conhece o registro atual para calcular as datas efetivas).
"""

from __future__ import annotations

from datetime import date


def validate_date_order(data_inicio: date | None, data_prevista_fim: date | None) -> None:
    if (
        data_inicio is not None
        and data_prevista_fim is not None
        and data_prevista_fim < data_inicio
    ):
        raise ValueError("data_prevista_fim deve ser maior ou igual a data_inicio")
