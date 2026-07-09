"""B5.1 — tabelas orcamento, orcamento_versao, orcamento_item (Módulo 2 — EAP)

Schema conforme docs/ESPEC.md § 7. Estrutura EAP em 3 níveis (Fase → Serviço →
Insumo) via *adjacency list* (`parent_id` self-FK) + *materialized path* (`path`,
`depth`) para varredura de subárvore em uma query.

Decisões de schema:
- `orcamento_status` enum ('rascunho','em_revisao','aguardando_aprovacao',
  'aprovado','rejeitado') — domínio fechado do ESPEC, mesmo padrão de obra_status
  e ticket_status (enum no Postgres, ver docs/CLAUDE.md).
- `company_id` DENORMALIZADO nas três tabelas + RLS `tenant_isolation` simples
  (mesmo precedente de ticket_mensagem: a versão/item herdam company_id do
  orçamento para a policy não precisar de join). versao/item cascateiam por
  company_id no mesmo statement do delete da company.
- `orcamento_item.parent_id` self-FK ON DELETE CASCADE: apagar uma fase leva a
  subárvore (serviços e insumos). `versao_id` CASCADE idem.
- `path TEXT`: caminho de ids dos ancestrais (estável sob reordenação — só o
  sort_order muda, não os ids). Descendentes de X = `path LIKE X.path || '.%'`.
  Preenchido pela aplicação no insert (B5.4). `depth` SMALLINT (0=F,1=S,2=I).
- `tipo CHAR(1)` CHECK ('F','S','I'): Fase, Serviço, Insumo/MO.
- `custo_total` GENERATED STORED (quantidade × preco_unitario): custo direto do
  nó folha, derivado pelo Postgres — nunca calculado em Python (impossível
  divergir). `subtotal` é agregado (com markup) pelo BudgetCalculator (B5.2).
- Precisão financeira: preco_unitario NUMERIC(18,6), custo/subtotal NUMERIC(18,2),
  markup/taxa/margem NUMERIC(5,4). **Proibido float** (docs/CLAUDE.md).
- Trigger `orcamento_item_lock_guard`: versão aprovada (`is_locked=true`) é um
  snapshot imutável — bloqueia INSERT/UPDATE/DELETE em orcamento_item no nível do
  banco (backstop; a API também checa e devolve 409). Ver ESPEC "aprovado bloqueia".
- `UNIQUE (orcamento_id, numero)`: revisões numeradas 1..N por orçamento.

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute(
        "CREATE TYPE orcamento_status AS ENUM "
        "('rascunho','em_revisao','aguardando_aprovacao','aprovado','rejeitado')"
    )

    # ---- orcamento -------------------------------------------------------
    op.create_table(
        "orcamento",
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
            "versao_atual",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="orcamento_status", create_type=False),
            nullable=False,
            server_default=sa.text("'rascunho'"),
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
    op.create_index("ix_orcamento_company_obra", "orcamento", ["company_id", "obra_id"])
    op.execute(
        "CREATE INDEX ix_orcamento_company_id_desc ON orcamento (company_id, id DESC) "
        "WHERE deleted_at IS NULL"
    )

    # ---- orcamento_versao -----------------------------------------------
    op.create_table(
        "orcamento_versao",
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
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "custo_direto",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "markup_global",
            sa.Numeric(5, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "taxa_adm",
            sa.Numeric(5, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "preco_venda",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "margem",
            sa.Numeric(5, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("curva_abc_json", postgresql.JSONB(), nullable=True),
        sa.Column("markup_por_fase_json", postgresql.JSONB(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("pdf_gerado_em", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "criado_por",
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
        sa.UniqueConstraint("orcamento_id", "numero", name="uq_versao_orcamento_numero"),
    )
    op.create_index(
        "ix_versao_company_orcamento", "orcamento_versao", ["company_id", "orcamento_id"]
    )

    # ---- orcamento_item --------------------------------------------------
    op.create_table(
        "orcamento_item",
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
            "versao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orcamento_versao.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orcamento_item.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("path", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("depth", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("tipo", sa.CHAR(1), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("unidade", sa.Text(), nullable=True),
        sa.Column(
            "quantidade",
            sa.Numeric(10, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "preco_unitario",
            sa.Numeric(18, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("markup_override", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "custo_total",
            sa.Numeric(18, 2),
            sa.Computed("quantidade * preco_unitario", persisted=True),
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("tipo IN ('F','S','I')", name="ck_item_tipo"),
    )
    op.create_index("ix_item_versao_parent", "orcamento_item", ["versao_id", "parent_id"])
    op.create_index("ix_item_versao_path", "orcamento_item", ["versao_id", "path"])
    # Ordena os irmãos de um nível na leitura da árvore (D5.1 completa isto).
    op.create_index(
        "ix_item_versao_sort", "orcamento_item", ["versao_id", "parent_id", "sort_order"]
    )

    # ---- trigger de bloqueio de versão aprovada -------------------------
    op.execute(
        """
        CREATE FUNCTION orcamento_item_lock_guard() RETURNS trigger AS $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM orcamento_versao v
            WHERE v.id = COALESCE(NEW.versao_id, OLD.versao_id) AND v.is_locked
          ) THEN
            RAISE EXCEPTION 'versao_travada: orcamento_item de versao aprovada e imutavel'
              USING ERRCODE = 'raise_exception';
          END IF;
          RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_orcamento_item_lock
          BEFORE INSERT OR UPDATE OR DELETE ON orcamento_item
          FOR EACH ROW EXECUTE FUNCTION orcamento_item_lock_guard()
        """
    )

    # ---- RLS por tenant --------------------------------------------------
    for table in ("orcamento", "orcamento_versao", "orcamento_item"):
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
