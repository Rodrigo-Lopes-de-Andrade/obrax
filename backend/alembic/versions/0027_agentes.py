"""Sprint 10 (Módulo 3 / Agentes IA) — fundação de dados (D10.1, D10.2)

Três tabelas do domínio de agentes, todas isoladas por tenant (RLS
`tenant_isolation`, mesmo padrão de `lgpd_request`/`ticket_mensagem`):

- `ai_permission` (B10.7, US-23): mapeia um número de WhatsApp → papel IA
  (`consultor`/`solicitador`/`aprovador`) e limites de gasto (diário/mensal, em
  centavos). UNIQUE (company_id, whatsapp_number) — um papel por número por
  tenant. Índice extra em `whatsapp_number` para o lookup do webhook.

- `agent_message` (B10.2, D10.1): fila/backup das mensagens recebidas do Uazap.
  Idempotência por `message_id` do provedor via UNIQUE (company_id, message_id):
  reprocessar o mesmo webhook não duplica trabalho. `status` acompanha o
  consumo pelo worker.
  NOTA D10.1: o SPRINTS/CLAUDE.md preveem particionamento RANGE mensal desta
  tabela. Particionar nativamente conflita com a UNIQUE global de idempotência
  (uma UNIQUE em tabela particionada precisa conter a chave de partição), e o
  repositório ainda não particiona nem `audit_log` — então, seguindo o mesmo
  diferimento pragmático do Redis (integrations/events.py), a tabela nasce
  não-particionada com a idempotência correta; a evolução para partição mensal
  é uma migration futura (expand-contract) quando o volume exigir.

- `agent_interaction` (B10.6, US-22): trilha das ações dos agentes (intenção,
  agente acionado, ação, resultado, custo). Diferente de `audit_log` (append-only
  por REVOKE), esta tabela permite marcar reversão (`reverted_at`/`reverted_by`),
  pois "reverter uma ação" (US-22) precisa carimbar a linha original; a reversão
  em si (ex: apagar a compra errada) é um efeito de domínio à parte. `cost_cents`
  alimenta o enforcement de limite de gasto (soma por janela diária/mensal).

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE ai_role AS ENUM ('consultor','solicitador','aprovador')")
    op.execute(
        "CREATE TYPE agent_message_status AS ENUM ('pendente','processando','concluido','erro')"
    )
    op.execute("CREATE TYPE agent_interaction_status AS ENUM ('ok','erro','revertido')")

    # ── ai_permission (B10.7, US-23) ───────────────────────────────────────
    op.create_table(
        "ai_permission",
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
        sa.Column("whatsapp_number", sa.Text(), nullable=False),
        sa.Column("role", postgresql.ENUM(name="ai_role", create_type=False), nullable=False),
        sa.Column("daily_limit_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("monthly_limit_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # D10.2: unicidade do número por tenant + lookup rápido por número.
    op.execute(
        "CREATE UNIQUE INDEX ux_ai_permission_company_number "
        "ON ai_permission (company_id, whatsapp_number)"
    )
    op.execute("CREATE INDEX ix_ai_permission_number ON ai_permission (whatsapp_number)")
    _enable_tenant_rls("ai_permission")

    # ── agent_message (B10.2, D10.1) ───────────────────────────────────────
    op.create_table(
        "agent_message",
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
        # message_id do provedor (Uazap) — chave de idempotência do webhook.
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column("whatsapp_number", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="agent_message_status", create_type=False),
            nullable=False,
            server_default=sa.text("'pendente'"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_agent_message_company_msgid "
        "ON agent_message (company_id, message_id)"
    )
    # Poll do worker (mensagens pendentes) e listagem recente.
    op.execute(
        "CREATE INDEX ix_agent_message_company_status ON agent_message (company_id, status, id)"
    )
    _enable_tenant_rls("agent_message")

    # ── agent_interaction (B10.6, US-22) ───────────────────────────────────
    op.create_table(
        "agent_interaction",
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
        # A mensagem que originou a interação (SET NULL: a trilha sobrevive à
        # limpeza/expurgo de mensagens antigas).
        sa.Column(
            "agent_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_message.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Obra alvo da interação (para filtro na auditoria, F10.2). SET NULL: a
        # trilha sobrevive à remoção da obra.
        sa.Column(
            "obra_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obras.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("whatsapp_number", sa.Text(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("agent", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="agent_interaction_status", create_type=False),
            nullable=False,
            server_default=sa.text("'ok'"),
        ),
        sa.Column("cost_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        # Reversão (US-22): quem/quando reverteu o efeito desta interação.
        sa.Column("reverted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "reverted_by",
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
    )
    op.execute(
        "CREATE INDEX ix_agent_interaction_company_id_desc "
        "ON agent_interaction (company_id, id DESC)"
    )
    # Enforcement de limite de gasto: soma cost_cents por número numa janela.
    op.execute(
        "CREATE INDEX ix_agent_interaction_spend "
        "ON agent_interaction (company_id, whatsapp_number, created_at)"
    )
    _enable_tenant_rls("agent_interaction")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
