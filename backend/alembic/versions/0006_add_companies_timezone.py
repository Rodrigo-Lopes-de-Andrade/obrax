"""D1.3 — migration de exemplo (ADD COLUMN) testada

Demonstra o fluxo forward-only pedido em D1.3: em vez de editar a migration
0004 (já "aplicada"), evoluímos o schema com uma nova migration que adiciona
uma coluna. Segue a regra do CLAUDE.md ("Squawk linter bloqueia ADD COLUMN
NOT NULL sem default"): a coluna é NOT NULL mas tem DEFAULT, portanto não
precisa de rewrite de tabela nem quebra linhas existentes.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-06
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    op.add_column(
        "companies",
        sa.Column(
            "timezone",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'America/Sao_Paulo'"),
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
