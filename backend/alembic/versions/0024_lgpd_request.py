"""B9.1 — tabela lgpd_request (Módulo Portal / LGPD, US-21)

Registra os pedidos LGPD do titular: **exportação** dos dados (right to data
portability) e **eliminação** (right to be forgotten). O SPRINTS lista duas
tabelas (`lgpd_request`, `export_job`), mas não há fila assíncrona no backend
ainda (mesma situação de app/integrations/notifications.py) — então o "job" é
processado de forma síncrona no request, exatamente como o PDF do orçamento
(`pdf_job.gerar_pdf`, "Gera (síncrono)"). Por isso `export_job` é dobrado
aqui: esta mesma linha carrega o estado do processamento (`status`), o artefato
gerado (`payload_path`) e o TTL do arquivo (`expires_at`, 7 dias).

Decisões de schema:
- `request_type` enum `lgpd_request_type ('export','delete')` e `status` enum
  `lgpd_status ('pendente','processando','concluido','erro')` — domínios fixos
  em Postgres (docs/CLAUDE.md), mesmo padrão de obra_status/orcamento_status.
- `company_id` FK CASCADE + RLS `tenant_isolation` (como as demais tabelas de
  domínio): o pedido pertence ao tenant e some com ele.
- `cliente_id` FK SET NULL nullable: o titular do pedido (para export/delete de
  um cliente específico). NULL = export do tenant inteiro (admin baixando tudo).
  SET NULL para o registro do pedido sobreviver à anonimização do cliente (B9.5).
- `requested_by` FK users SET NULL: quem solicitou sobrevive à sua própria
  remoção LGPD (o pedido é trilha de conformidade).
- `payload_path` TEXT nullable: chave do ZIP no storage (nunca a URL — regra do
  projeto, docs/CLAUDE.md; a URL assinada é gerada sob demanda no download).
- `expires_at` nullable: instante em que o arquivo exportado expira (created_at
  + 7 dias). Depois disso o download responde 410 (link de vida curta, US-21).
- `error_detail` nullable: mensagem curta quando `status='erro'`.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE lgpd_request_type AS ENUM ('export','delete')")
    op.execute("CREATE TYPE lgpd_status AS ENUM ('pendente','processando','concluido','erro')")

    op.create_table(
        "lgpd_request",
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
        # SET NULL: o pedido é trilha de conformidade e sobrevive à anonimização
        # (B9.5) do cliente titular. NULL = export do tenant inteiro.
        sa.Column(
            "cliente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "request_type",
            postgresql.ENUM(name="lgpd_request_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="lgpd_status", create_type=False),
            nullable=False,
            server_default=sa.text("'pendente'"),
        ),
        # SET NULL: quem solicitou sobrevive à sua própria remoção LGPD.
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload_path", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_lgpd_request_company_id_desc ON lgpd_request (company_id, id DESC)"
    )

    op.execute("ALTER TABLE lgpd_request ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lgpd_request FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY lgpd_request_tenant_isolation ON lgpd_request
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
