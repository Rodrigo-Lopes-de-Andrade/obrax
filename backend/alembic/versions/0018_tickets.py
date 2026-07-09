"""B4.1 — tabelas ticket e ticket_mensagem (chamados/tickets, Módulo 1)

Schema conforme docs/ESPEC.md § 7 (nomes no singular, como documento/obra_membro).

Decisões de schema:
- `status` como enum `ticket_status` (aberto/andamento/resolvido/fechado): o
  SPRINTS pede enum e o domínio é fixo — casa com o precedente `obra_status`
  (o ESPEC escreve `status TEXT`; seguimos o enum pela disciplina de domínio
  fechado em Postgres, docs/CLAUDE.md).
- `company_id` denormalizado nas duas tabelas + RLS `tenant_isolation` simples
  (como clientes/obras/documento). ticket_mensagem herda `company_id` do ticket
  para não precisar de join na policy.
- `obra_id`/`ticket_id` NO ACTION vs CASCADE: `ticket.obra_id` NO ACTION (não
  apaga obra com tickets; cascade por company remove no mesmo statement).
  `ticket_mensagem.ticket_id` CASCADE (apagar o ticket leva as mensagens).
- `created_by`/`author_id` FK users ON DELETE SET NULL: o registro sobrevive à
  remoção (LGPD) de quem criou.
- `attachment_paths TEXT[]` default '{}': caminhos no storage (até 5 anexos,
  validado na API — B4.3).
- `descricao` nullable (obrigatoriedade/limite de 5KB é validação de API).

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE ticket_status AS ENUM ('aberto','andamento','resolvido','fechado')")

    op.create_table(
        "ticket",
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
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="ticket_status", create_type=False),
            nullable=False,
            server_default=sa.text("'aberto'"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_ticket_company_status", "ticket", ["company_id", "status"])
    op.create_index("ix_ticket_company_obra", "ticket", ["company_id", "obra_id"])
    op.execute(
        "CREATE INDEX ix_ticket_company_id_desc ON ticket (company_id, id DESC) "
        "WHERE deleted_at IS NULL"
    )

    op.create_table(
        "ticket_mensagem",
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
            "ticket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ticket.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "attachment_paths",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Carrega o histórico de um ticket em ordem cronológica (id v7 ~ tempo).
    op.create_index("ix_ticket_mensagem_ticket", "ticket_mensagem", ["ticket_id", "id"])

    for table in ("ticket", "ticket_mensagem"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
              USING (company_id = current_setting('app.company_id', true)::uuid)
              WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
            """
        )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
