"""B1.4 — tabela consumed_tokens (magic links single-use + revogação refresh)

Registra o `jti` de tokens JWT já utilizados/revogados (ver
docs/CLAUDE.md > "O que NÃO Tocar": nunca deletar entradas válidas; um job
de limpeza diário — fora do escopo desta sprint — cuida de expurgar linhas
com `expires_at` no passado).

Sem `company_id`: não é dado de domínio por tenant (docs/ESPEC.md § 7 não
lista essa coluna para esta tabela) — é bookkeeping de segurança global,
por isso sem RLS (análogo a uma deny-list de JWT, não a uma entidade de
negócio isolada por empresa).

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-06
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "consumed_tokens",
        sa.Column("jti", sa.Text(), primary_key=True),
        sa.Column(
            "consumed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_consumed_tokens_expires_at", "consumed_tokens", ["expires_at"])


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
