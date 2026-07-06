"""Tabela `consumed_tokens` — registro de JTIs de tokens JWT de uso único.

Serve dois propósitos (ver docs/CLAUDE.md > "O que NÃO Tocar" — nunca
deletar entradas válidas; job de limpeza diário cuida de expirados):

1. Magic links (B1.4): ao consumir um token `purpose`/`type=magic`, o `jti`
   é inserido aqui; uma segunda tentativa de consumo com o mesmo `jti` falha
   (já existe na tabela) → 401.
2. Revogação de refresh token no logout (B1.3): o `jti` do refresh token é
   inserido aqui no logout; `POST /auth/refresh` rejeita qualquer `jti` já
   presente na tabela.

Sem `company_id`: não é dado de domínio por tenant (ver docs/ESPEC.md § 7,
schema não lista `company_id` para esta tabela) — é bookkeeping de segurança
de infraestrutura, análogo a uma deny-list de JWT. Por isso não tem RLS.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConsumedToken(Base):
    __tablename__ = "consumed_tokens"

    jti: Mapped[str] = mapped_column(Text, primary_key=True)
    consumed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
