"""S-F1 — obra_fase: a fase como identidade estável da obra (Módulos 5 e 6)

Cria `obra_fase` conforme Dicionário de Dados §4.1. É o eixo de apropriação do
módulo financeiro: a fase sobrevive à revisão de orçamento (reconciliação por
`codigo`, RN-F03) e nunca é apagada, só marcada `ativa = false`.

RLS pelo template do Dicionário §2 (não o da 0023): ENABLE + FORCE, policy com
USING e WITH CHECK usando `app_current_company_id()` (0030). O GRANT a
`app_user`/`app_admin` vem do `ALTER DEFAULT PRIVILEGES` da 0001 (ESPEC §7.3) e é
conferido no catálogo por `scripts/check_schema_financeiro.py`.

`orcamento_versao_id` é rastreabilidade, não dependência (Dicionário §4.1):
ON DELETE SET NULL. FK para `obras` é NO ACTION (Dicionário §1).

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "obra_fase",
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
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("valor_orcado", sa.Numeric(18, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "orcamento_versao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orcamento_versao.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("obra_id", "codigo", name="uq_obra_fase_obra_codigo"),
        sa.CheckConstraint("valor_orcado >= 0", name="ck_obra_fase_valor_orcado"),
    )
    op.create_index(
        "ix_obra_fase_company_obra_sort", "obra_fase", ["company_id", "obra_id", "sort_order"]
    )

    op.execute("ALTER TABLE obra_fase ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE obra_fase FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY obra_fase_tenant_isolation ON obra_fase
          USING (company_id = app_current_company_id())
          WITH CHECK (company_id = app_current_company_id())
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS obra_fase_tenant_isolation ON obra_fase")
    op.drop_index("ix_obra_fase_company_obra_sort", table_name="obra_fase")
    op.drop_table("obra_fase")
