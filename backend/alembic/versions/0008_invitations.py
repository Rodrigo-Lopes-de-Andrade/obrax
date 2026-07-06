"""B1.5 — tabela invitations (convites de usuário, US-19 prep)

Schema conforme docs/ESPEC.md § 7. `token_hash` é o SHA-256 (hex) do token
opaco de 32 bytes URL-safe entregue ao convidado — nunca armazenamos o
token em claro (comparação de posse é feita hasheando o token recebido e
comparando com esta coluna).

RLS: tem `company_id`, então segue o padrão de isolamento por tenant.
`FORCE ROW LEVEL SECURITY` inclusive para o dono da tabela (mesmo racional
de `alembic/versions/0005_rls_policies.py`). A leitura desta tabela durante
o fluxo de aceitar convite roda via role `app_admin` (BYPASSRLS) — o
convidado só tem o token em mãos, sem tenant conhecido ainda.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "invitations",
        sa.Column("token_hash", sa.CHAR(64), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", postgresql.ENUM(name="user_role", create_type=False), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_invitations_company_id", "invitations", ["company_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])

    op.execute("ALTER TABLE invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invitations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY invitations_tenant_isolation ON invitations
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
