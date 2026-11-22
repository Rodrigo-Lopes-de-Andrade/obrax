"""Schemas de análise (ESPEC §6.3): orçado x realizado, Curva S, fluxo de caixa.

Valores monetários são `Decimal`. `percentual_consumido` é **fração** (1.05 =
105%) e pode passar de 1 quando estoura.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.financeiro.schemas._types import DinheiroOut, FracaoOut, Periodicidade


class FaseOrcadoRealizado(BaseModel):
    """Uma fase. `percentual_consumido` = (realizado + comprometido) / orcado, em
    fração; nulo quando `orcado` é zero. `estourou` segue RN-F04."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    codigo: str
    descricao: str
    ativa: bool
    orcado: DinheiroOut
    realizado: DinheiroOut
    comprometido: DinheiroOut
    saldo: DinheiroOut
    percentual_consumido: FracaoOut | None
    estourou: bool


class TotaisOrcadoRealizado(BaseModel):
    """Soma das fases (CA-F11.3). `percentual_consumido` é fração."""

    model_config = ConfigDict(extra="forbid")

    orcado: DinheiroOut
    realizado: DinheiroOut
    comprometido: DinheiroOut
    saldo: DinheiroOut
    percentual_consumido: FracaoOut | None


class OrcadoRealizadoOut(BaseModel):
    """Orçado x realizado por fase. `tem_orcamento_aprovado=false` é o estado
    vazio de CA-F11.4/RN-F01 (não zeros)."""

    model_config = ConfigDict(extra="forbid")

    obra_id: UUID
    tem_orcamento_aprovado: bool
    orcamento_versao_id: UUID | None
    fases: list[FaseOrcadoRealizado]
    totais: TotaisOrcadoRealizado


class CurvaSPonto(BaseModel):
    """Ponto acumulado por período: planejado (cronograma), físico (medições
    aprovadas) e realizado financeiro (despesas pagas)."""

    model_config = ConfigDict(extra="forbid")

    periodo_id: UUID
    numero: int
    inicio: date
    fim: date
    corrente: bool
    planejado_acumulado: DinheiroOut
    medido_acumulado: DinheiroOut
    realizado_acumulado: DinheiroOut


class CurvaSOut(BaseModel):
    """`tem_cronograma=false` é o estado vazio de CA-F12.4."""

    model_config = ConfigDict(extra="forbid")

    obra_id: UUID
    tem_cronograma: bool
    pontos: list[CurvaSPonto]


class FluxoCaixaPeriodo(BaseModel):
    """Um período do fluxo; períodos sem movimento aparecem com zero (CA-F13.3).

    - `saldo_previsto` = `entradas_previstas` − `saidas_previstas` do período.
    - `saldo_realizado` = `entradas_realizadas` (recebido) − `saidas_realizadas`
      (pago) do período.
    - `saldo_previsto_acumulado` / `saldo_realizado_acumulado`: soma corrente do
      respectivo saldo desde o primeiro período do intervalo, inclusive este.
    """

    model_config = ConfigDict(extra="forbid")

    inicio: date
    fim: date
    saidas_previstas: DinheiroOut
    saidas_realizadas: DinheiroOut
    entradas_previstas: DinheiroOut
    entradas_realizadas: DinheiroOut
    saldo_previsto: DinheiroOut
    saldo_realizado: DinheiroOut
    saldo_previsto_acumulado: DinheiroOut
    saldo_realizado_acumulado: DinheiroOut


class FluxoCaixaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obra_id: UUID | None
    de: date
    ate: date
    periodicidade: Periodicidade
    periodos: list[FluxoCaixaPeriodo]
