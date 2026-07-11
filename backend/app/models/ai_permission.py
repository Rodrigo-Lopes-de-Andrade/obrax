"""Tabela `ai_permission` — papel IA + limites de gasto por número de WhatsApp
(B10.7, US-23). Ver `alembic/versions/0027_agentes.py`.

RLS: `company_id`, isolamento por tenant. UNIQUE (company_id, whatsapp_number).
Limites em centavos (inteiro) para evitar float em dinheiro (docs/CLAUDE.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiPermission(Base):
    __tablename__ = "ai_permission"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    whatsapp_number: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(ENUM(name="ai_role", create_type=False), nullable=False)
    daily_limit_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    monthly_limit_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
