"""Tabela `documento` — arquivos do GED de uma obra (B3.1 / Módulo 1).
Ver `alembic/versions/0014_documento.py`.

RLS: tem `company_id`, isolamento por tenant (mesma policy de clientes/obras).
Colunas do ciclo de upload (`storage_path`, `size_bytes`, `sha256`, `ocr_text`,
`categoria`) são nullable: a linha nasce no POST e é completada no confirm
(B3.2/B3.3). Dedup por conteúdo via UNIQUE (obra_id, sha256).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CHAR, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Criado em alembic/versions/0014_documento.py — `create_type=False` porque o
# tipo já existe no Postgres (enums são criados via migration).
documento_tipo = PGEnum(
    "projeto",
    "contrato",
    "nota_fiscal",
    "foto",
    "outro",
    name="documento_tipo",
    create_type=False,
)


class Documento(Base):
    __tablename__ = "documento"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v7()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    obra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("obras.id"), nullable=False
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(documento_tipo, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[str | None] = mapped_column(Text, nullable=True)
    visivel_cliente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
