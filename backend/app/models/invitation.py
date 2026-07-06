"""Tabela `invitations` — convites de usuário (B1.5 / US-19 prep).

RLS: tem `company_id` (dado de domínio), então segue o mesmo padrão de
isolamento por tenant das demais tabelas — a única exceção é a leitura pelo
fluxo de aceitar convite (`GET/POST /auth/accept-invite`), que roda via role
`app_admin` (BYPASSRLS) porque, nesse ponto, o usuário só tem o token opaco
em mãos, sem JWT/tenant conhecido ainda (mesmo raciocínio da policy de
INSERT em `users`, ver `alembic/versions/0005_rls_policies.py`).

`token_hash`: SHA-256 (hex, 64 chars) do token opaco de 32 bytes URL-safe
enviado ao convidado; nunca armazenamos o token em claro.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, text
from sqlalchemy.dialects.postgresql import CITEXT, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.user_company_role import user_role


class Invitation(Base):
    __tablename__ = "invitations"

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(user_role, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
