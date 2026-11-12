"""Schemas do cronograma físico-financeiro (ESPEC §6.1, Dicionário §4.4-4.6).

Todo percentual é `Decimal` **como fração** (0.25 = 25%), nunca 0-100.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.financeiro.schemas._types import DinheiroOut, Fracao, FracaoOut, Periodicidade


class CronogramaCreate(BaseModel):
    """Cria o cronograma a partir da versão aprovada (CA-F01.x).

    `numero_periodos` define a distribuição linear inicial; ausente, o service
    deriva da obra.
    """

    model_config = ConfigDict(extra="forbid")

    periodicidade: Periodicidade
    data_inicio: date
    numero_periodos: int | None = Field(default=None, ge=1, le=520)


class CronogramaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    obra_id: UUID
    orcamento_versao_id: UUID
    periodicidade: Periodicidade
    data_inicio: date
    bloqueado_em: datetime | None
    created_at: datetime


class PeriodoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    numero: int
    inicio: date
    fim: date


class AlocacaoOut(BaseModel):
    """Célula fase x período. `percentual_planejado` é fração do valor da fase."""

    model_config = ConfigDict(extra="forbid")

    periodo_id: UUID
    percentual_planejado: FracaoOut
    valor_planejado: DinheiroOut


class FaseGradeOut(BaseModel):
    """Linha da grade: uma fase com suas alocações por período."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    codigo: str
    descricao: str
    valor_orcado: DinheiroOut
    alocacoes: list[AlocacaoOut]


class CronogramaGradeOut(BaseModel):
    """Grade fase x período. Percentuais são frações (0.25 = 25%)."""

    model_config = ConfigDict(extra="forbid")

    cronograma: CronogramaOut
    periodos: list[PeriodoOut]
    fases: list[FaseGradeOut]


class AlocacaoIn(BaseModel):
    """Célula enviada no PUT. `percentual_planejado` é fração (0.25 = 25%)."""

    model_config = ConfigDict(extra="forbid")

    obra_fase_id: UUID
    periodo_id: UUID
    percentual_planejado: Fracao


class AlocacoesPut(BaseModel):
    """Substitui o conjunto inteiro de alocações (RN-F07: cada fase fecha em 1)."""

    model_config = ConfigDict(extra="forbid")

    alocacoes: list[AlocacaoIn] = Field(min_length=1)
