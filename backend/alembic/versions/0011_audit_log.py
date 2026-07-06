"""B2.4 — audit_log + triggers de auditoria em clientes e obras

Registro append-only de toda mutação (INSERT/UPDATE/DELETE) nas tabelas de
domínio de Gestão de Obras. O soft delete da API é um UPDATE (`deleted_at`),
então cai no ramo UPDATE do trigger; o ramo DELETE cobre remoções físicas
(cascade ao apagar a company, operações administrativas).

Decisões de schema:
- Sem FK em `company_id`/`actor_id`: log de auditoria é imutável e deve
  sobreviver à remoção da company/usuário referenciados (e não interferir nos
  cascades de DELETE). O isolamento por tenant continua via RLS na coluna
  `company_id` (mesma policy das demais tabelas).
- `actor_id`/`ip` vêm de GUCs de sessão (`app.actor_id`, `app.client_ip`)
  setadas por request em `get_db` (app/core/deps.py) — o trigger as lê com
  `current_setting(..., true)` e converte '' → NULL. Operações fora de uma
  request (cascade/admin via role `obrax`) gravam `actor_id`/`ip` NULL.
- `before`/`after` são `to_jsonb(OLD)`/`to_jsonb(NEW)` — snapshot completo da
  linha em cada lado da mutação.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE audit_action AS ENUM ('INSERT','UPDATE','DELETE')")

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v7()"),
        ),
        # Sem FK (ver docstring): coluna crua para isolamento por RLS.
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(name="audit_action", create_type=False),
            nullable=False,
        ),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "CREATE INDEX ix_audit_log_company_created_at ON audit_log (company_id, created_at DESC)"
    )
    op.create_index("ix_audit_log_record", "audit_log", ["table_name", "record_id"])

    # RLS: mesmo padrão tenant_isolation das demais tabelas com company_id.
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_log_tenant_isolation ON audit_log
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )

    # Trigger genérico: serve qualquer tabela com colunas `id` e `company_id`.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_trigger() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
          v_actor uuid := NULLIF(current_setting('app.actor_id', true), '')::uuid;
          v_ip    inet := NULLIF(current_setting('app.client_ip', true), '')::inet;
        BEGIN
          IF TG_OP = 'INSERT' THEN
            INSERT INTO audit_log
              (company_id, actor_id, table_name, record_id, action, before, after, ip)
              VALUES (NEW.company_id, v_actor, TG_TABLE_NAME, NEW.id, 'INSERT',
                      NULL, to_jsonb(NEW), v_ip);
            RETURN NEW;
          ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO audit_log
              (company_id, actor_id, table_name, record_id, action, before, after, ip)
              VALUES (NEW.company_id, v_actor, TG_TABLE_NAME, NEW.id, 'UPDATE',
                      to_jsonb(OLD), to_jsonb(NEW), v_ip);
            RETURN NEW;
          ELSE  -- DELETE
            INSERT INTO audit_log
              (company_id, actor_id, table_name, record_id, action, before, after, ip)
              VALUES (OLD.company_id, v_actor, TG_TABLE_NAME, OLD.id, 'DELETE',
                      to_jsonb(OLD), NULL, v_ip);
            RETURN OLD;
          END IF;
        END;
        $$
        """
    )

    for table in ("clientes", "obras"):
        op.execute(
            f"CREATE TRIGGER audit_{table} "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION audit_trigger()"
        )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
