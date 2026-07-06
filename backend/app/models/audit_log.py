"""Tabela `audit_log` — trilha de auditoria append-only das mutações em
`clientes`/`obras` (B2.4). Ver `alembic/versions/0011_audit_log.py`.

Preenchida por trigger no banco, não pela aplicação — este modelo apenas
espelha o schema. Sem FK em `company_id`/`actor_id` (log imutável, sobrevive à
remoção do referenciado); isolamento por tenant via RLS na coluna `company_id`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    table_name: Mapped[str] = mapped_column(Text, nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 'INSERT' | 'UPDATE' | 'DELETE' — enum audit_action criado na migration.
    action: Mapped[str] = mapped_column(
        ENUM(name="audit_action", create_type=False), nullable=False
    )
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
