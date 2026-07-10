"""B9.3 — tabela orcamento_aprovacao + auditoria do orçamento (US-20)

Registra a decisão do cliente sobre um orçamento tomada pelo portal
(aprovar/rejeitar), com a evidência de conformidade exigida pelo SPRINTS
("registra timestamp + IP + signature"): quem assinou, o comentário livre, a
imagem da assinatura (chave no storage) e o IP de origem.

Decisões de schema:
- `aprovacao_decisao` enum ('aprovado','rejeitado') — domínio fixo em Postgres.
- `company_id` FK CASCADE + RLS `tenant_isolation` (padrão das demais tabelas).
  A escrita vem do portal, sob `get_portal_db` (app.company_id do token).
- `orcamento_id` FK CASCADE (apagar o orçamento leva suas aprovações);
  `versao_id` FK SET NULL (a decisão é sobre a versão vigente no momento, mas o
  registro sobrevive a uma eventual remoção da versão).
- `assinatura_path` guarda só a chave da imagem no storage (nunca a URL — regra
  do projeto). `assinado_por` é o nome digitado pelo cliente (opcional).
- `ip INET` vem do `app.client_ip` da request do portal.

Além da tabela, anexamos o `audit_trigger()` genérico (0011) à tabela
`orcamento`: a mudança de status na aprovação/rejeição passa a gerar linha em
`audit_log` (com IP), satisfazendo o critério "audit_log" da US-20 — mesmo
precedente de documento (0015).

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE aprovacao_decisao AS ENUM ('aprovado','rejeitado')")

    op.create_table(
        "orcamento_aprovacao",
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
            "orcamento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orcamento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "versao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orcamento_versao.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "decisao",
            postgresql.ENUM(name="aprovacao_decisao", create_type=False),
            nullable=False,
        ),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("assinatura_path", sa.Text(), nullable=True),
        sa.Column("assinado_por", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_orcamento_aprovacao_orcamento", "orcamento_aprovacao", ["orcamento_id", "id"]
    )

    op.execute("ALTER TABLE orcamento_aprovacao ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE orcamento_aprovacao FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY orcamento_aprovacao_tenant_isolation ON orcamento_aprovacao
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )

    # Auditoria da mudança de status do orçamento (aprovação/rejeição do portal
    # cai no ramo UPDATE, com IP do app.client_ip). Trigger genérico da 0011.
    op.execute(
        "CREATE TRIGGER audit_orcamento "
        "AFTER INSERT OR UPDATE OR DELETE ON orcamento "
        "FOR EACH ROW EXECUTE FUNCTION audit_trigger()"
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
