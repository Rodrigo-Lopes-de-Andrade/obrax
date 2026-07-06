"""Tabela `user_company_role` — associação N:N entre `users` e `companies`,
com o papel (role) do usuário dentro de cada empresa.

Chave primária composta `(company_id, user_id)`: `company_id` é a coluna
líder para favorecer o padrão de acesso mais comum (tudo é filtrado por
tenant primeiro). Um índice extra em `user_id` cobre a busca reversa
("em quais empresas este usuário atua").
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Criado em alembic/versions/0003_enums.py — `create_type=False` porque o
# tipo já existe no Postgres.
user_role = PGEnum(
    "owner",
    "admin",
    "gestor",
    "orcamentista",
    "financeiro",
    "viewer",
    "campo",
    "ai",
    name="user_role",
    create_type=False,
)


class UserCompanyRole(Base):
    __tablename__ = "user_company_role"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(user_role, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
