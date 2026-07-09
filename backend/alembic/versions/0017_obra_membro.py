"""B3.5 — tabela obra_membro (equipes de obra, Módulo 1)

Vincula usuários a uma obra com um papel de campo (mestre, eletricista, pintor,
…). Schema conforme docs/ESPEC.md § 7.

Decisões de schema:
- `papel TEXT` (não enum): o ESPEC define TEXT e os papéis de campo são um
  conjunto aberto — enum exigiria migration a cada novo ofício. A validação
  fica na API (não-vazio).
- `company_id` denormalizado + RLS `tenant_isolation` simples (como
  clientes/obras/documento). obra_membro pertence a uma única empresa (via a
  obra), então não precisa do EXISTS que `users` usa por ser identidade global.
- `obra_id` NO ACTION (não deixa apagar obra com membros; o cascade por company
  remove os vínculos no mesmo statement). `user_id` CASCADE: remover o usuário
  (LGPD) leva junto seus vínculos.
- UNIQUE parcial `(obra_id, user_id) WHERE deleted_at IS NULL`: um usuário é
  membro ativo de uma obra no máximo uma vez, mas pode ser re-adicionado após
  remoção (soft delete) sem colidir.

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "obra_membro",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v7()"),
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "obra_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obras.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_obra_membro_ativo ON obra_membro (obra_id, user_id) "
        "WHERE deleted_at IS NULL"
    )
    op.execute("CREATE INDEX ix_obra_membro_obra ON obra_membro (obra_id) WHERE deleted_at IS NULL")

    op.execute("ALTER TABLE obra_membro ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE obra_membro FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY obra_membro_tenant_isolation ON obra_membro
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
