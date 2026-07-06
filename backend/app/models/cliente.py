"""Tabela `clientes` — pessoas físicas/jurídicas atendidas por cada empresa
(B2.1 / Módulo 1). Ver `alembic/versions/0009_clientes_obras.py`.

RLS: tem `company_id`, então segue o padrão de isolamento por tenant
(`alembic/versions/0010_rls_clientes_obras.py`). O mesmo CPF/CNPJ pode
existir em empresas diferentes — a unicidade é `(company_id, documento)`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    # 'PF' | 'PJ' — travado por CHECK constraint na migration.
    tipo_pessoa: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    documento: Mapped[str] = mapped_column(CITEXT, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    telefone: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
