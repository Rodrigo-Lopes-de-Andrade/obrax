"""Tabela `agent_message` — fila/backup das mensagens do Uazapi (B10.2, D10.1).
Ver `alembic/versions/0027_agentes.py`.

RLS: `company_id`, isolamento por tenant. Idempotência do webhook via
UNIQUE (company_id, message_id) — `message_id` é o id do provedor.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentMessage(Base):
    __tablename__ = "agent_message"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        ENUM(name="agent_message_status", create_type=False),
        nullable=False,
        server_default=text("'pendente'"),
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
