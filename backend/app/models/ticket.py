"""Tabela `ticket` — chamados/ocorrências de uma obra (B4.1 / Módulo 1).
Ver `alembic/versions/0018_tickets.py`.

RLS: tem `company_id`, isolamento por tenant (mesma policy de clientes/obras).
`status` é o enum `ticket_status` (criado na migration).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ticket_status = PGEnum(
    "aberto",
    "andamento",
    "resolvido",
    "fechado",
    name="ticket_status",
    create_type=False,
)


class Ticket(Base):
    __tablename__ = "ticket"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    obra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("obras.id"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        ticket_status, nullable=False, server_default=text("'aberto'")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
