"""Tabela `obras` — o projeto/reforma gerido para um cliente (B2.1 / Módulo 1).
Ver `alembic/versions/0009_clientes_obras.py`.

RLS: tem `company_id`, isolamento por tenant
(`alembic/versions/0010_rls_clientes_obras.py`). `valor_contrato` é
`NUMERIC(18,2)` → mapeado para `Decimal` (nunca float — docs/CLAUDE.md >
Precisão financeira).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Criado em alembic/versions/0009_clientes_obras.py — `create_type=False`
# porque o tipo já existe no Postgres (enums são criados via migration).
obra_status = PGEnum(
    "planejamento",
    "execucao",
    "pausada",
    "concluida",
    "cancelada",
    name="obra_status",
    create_type=False,
)


class Obra(Base):
    __tablename__ = "obras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        obra_status, nullable=False, server_default=text("'planejamento'")
    )
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_prevista_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_real_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_contrato: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
