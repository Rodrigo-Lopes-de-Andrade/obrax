"""B7.1 — tabela checklist_item (checklist diária de campo, US-16).

Itens de checklist de uma obra (ex.: "Conferir EPIs", "Registrar avanço da
laje"). Marcados como concluídos em campo — o app mobile opera offline e
sincroniza os toggles depois (Sprint 7 › Dexie queue), então cada linha carrega
`completed` + `completed_at`.

Decisões de schema (mesmo padrão de obra_membro / documento):
- `company_id` denormalizado + RLS `tenant_isolation` simples: o item pertence
  a uma única empresa (via a obra).
- `obra_id` NO ACTION (não deixa apagar obra com itens; o cascade por company
  remove no mesmo statement).
- `sort_order` INT para ordenação estável na listagem; `titulo` TEXT (validação
  não-vazio na API).
- Soft delete (`deleted_at`) — histórico preservado, mesma convenção do módulo.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "checklist_item",
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
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Listagem por obra, ordenada, ignorando removidos (índice cobre o filtro RLS
    # + ORDER BY sort_order, created_at).
    op.execute(
        "CREATE INDEX ix_checklist_obra_order "
        "ON checklist_item (obra_id, sort_order, created_at) "
        "WHERE deleted_at IS NULL"
    )

    op.execute("ALTER TABLE checklist_item ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE checklist_item FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY checklist_item_tenant_isolation ON checklist_item
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
