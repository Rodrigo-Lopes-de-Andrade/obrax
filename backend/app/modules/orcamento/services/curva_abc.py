"""B6.1 — Curva ABC (US-14): classifica os insumos de uma versão em A/B/C por
custo direto acumulado (regra 80/15/5, docs/SPRINTS.md § B6.1).

Ordena os itens-folha por custo decrescente e classifica pela participação
*acumulada antes* de incluir o item — assim o item de maior custo cai sempre em
A, mesmo quando sozinho já passa de 80%. A vai até 80% do custo, B de 80% a 95%,
C o restante.

**Proibido float** — tudo em `Decimal` (docs/CLAUDE.md). Fonte única da curva:
`budget_calculator.recalcular` (B5.2) coleta as folhas e persiste o resultado em
`orcamento_versao.curva_abc_json` (D6.1); o endpoint só lê o JSON denormalizado.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from app.modules.orcamento.schemas import AbcClasse, AbcItem, CurvaAbc

_PCT = Decimal("0.0001")
_LIMIAR_A = Decimal("0.80")
_LIMIAR_B = Decimal("0.95")
_CLASSES: tuple[Literal["A", "B", "C"], ...] = ("A", "B", "C")
_ZERO_PCT = Decimal("0.0000")


def classificar(leaves: list[dict[str, Any]]) -> CurvaAbc:
    """Classifica as folhas (dicts com id, codigo, descricao, unidade, custo) em
    A/B/C. `custo` já vem em centavos (Decimal), calculado pelo motor de cálculo."""
    total = sum((leaf["custo"] for leaf in leaves), Decimal(0))
    # Custo desc; desempate estável por id p/ resultado determinístico.
    ordenados = sorted(leaves, key=lambda x: (-x["custo"], str(x["id"])))

    itens: list[AbcItem] = []
    acumulado = Decimal(0)
    for leaf in ordenados:
        custo: Decimal = leaf["custo"]
        antes = acumulado  # participação acumulada ANTES de incluir este item
        acumulado += custo
        classe: Literal["A", "B", "C"]
        if total <= 0:
            classe = "C"
        elif antes < _LIMIAR_A * total:
            classe = "A"
        elif antes < _LIMIAR_B * total:
            classe = "B"
        else:
            classe = "C"
        itens.append(
            AbcItem(
                id=leaf["id"],
                codigo=leaf["codigo"],
                descricao=leaf["descricao"],
                unidade=leaf["unidade"],
                custo=custo,
                pct=_pct(custo, total),
                pct_acumulado=_pct(acumulado, total),
                classe=classe,
            )
        )

    classes: list[AbcClasse] = []
    for nome in _CLASSES:
        grupo = [it for it in itens if it.classe == nome]
        custo_classe = sum((it.custo for it in grupo), Decimal(0))
        classes.append(
            AbcClasse(
                classe=nome, count=len(grupo), custo=custo_classe, pct=_pct(custo_classe, total)
            )
        )

    return CurvaAbc(custo_total=total, itens=itens, classes=classes)


def _pct(parte: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return _ZERO_PCT
    return (parte / total).quantize(_PCT, ROUND_HALF_UP)
