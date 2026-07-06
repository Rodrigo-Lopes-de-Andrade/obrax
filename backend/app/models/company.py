"""Tabela `companies` — o tenant raiz do sistema multi-empresa.

RLS: policy `companies_tenant_isolation` restringe cada sessão a enxergar
apenas a linha cujo `id` bate com `current_setting('app.company_id')`
(ver alembic/versions/0005_rls_policies.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Criado em alembic/versions/0003_enums.py — `create_type=False` porque o
# tipo já existe no Postgres (enums são criados via migration, nunca pelo ORM).
company_tier = PGEnum(
    "starter",
    "pro",
    "enterprise",
    name="company_tier",
    create_type=False,
)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    cnpj: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    razao_social: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(company_tier, nullable=False, server_default=text("'starter'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Adicionada em alembic/versions/0006_add_companies_timezone.py — migration
    # de exemplo (ADD COLUMN NOT NULL com DEFAULT) para validar o fluxo forward-only.
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'America/Sao_Paulo'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
