"""B5.6 / D5.1 — catálogo de insumos (SINAPI) + índices EAP complementares.

`insumo` é o catálogo de composições/insumos. `company_id` NULLABLE
(docs/ESPEC.md § 7): NULL = catálogo SINAPI global (público, semeado via
app_admin); não-nulo = insumo customizado do tenant. A RLS deixa cada tenant
ler o global + os seus, mas só escrever nos seus (o global vem do seed admin).

Busca por descrição via índice GIN trigram (pg_trgm) — alvo <500ms em 10k itens
(B5.6). `codigo` CITEXT (case-insensitive). `preco_unitario` NUMERIC(12,4).

D5.1: reforça a varredura de árvore da EAP com um índice extra por profundidade
para as queries de tree do builder.

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.create_table(
        "insumo",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v7()"),
        ),
        # NULL = catálogo SINAPI global; não-nulo = insumo próprio do tenant.
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("codigo", postgresql.CITEXT(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("unidade", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("preco_unitario", sa.Numeric(12, 4), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Busca fuzzy por descrição (autocomplete servidor-side, B5.6/F5.6).
    op.execute("CREATE INDEX ix_insumo_descricao_trgm ON insumo USING gin (descricao gin_trgm_ops)")
    op.create_index("ix_insumo_categoria", "insumo", ["categoria"])
    # Unicidade de código: uma linha por código no catálogo global e uma por
    # (tenant, código) nos customizados (NULLs de company_id não são distintos
    # entre si num UNIQUE comum — daí os índices parciais).
    op.execute(
        "CREATE UNIQUE INDEX uq_insumo_sinapi_codigo ON insumo (codigo) WHERE company_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_insumo_tenant_codigo ON insumo (company_id, codigo) "
        "WHERE company_id IS NOT NULL"
    )

    op.execute("ALTER TABLE insumo ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE insumo FORCE ROW LEVEL SECURITY")
    # Leitura: catálogo global (company_id IS NULL) + insumos do próprio tenant.
    op.execute(
        """
        CREATE POLICY insumo_read ON insumo FOR SELECT
          USING (
            company_id IS NULL
            OR company_id = current_setting('app.company_id', true)::uuid
          )
        """
    )
    # Escrita: só nos insumos do próprio tenant (o global vem do seed admin).
    op.execute(
        """
        CREATE POLICY insumo_write ON insumo FOR ALL
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )

    # D5.1 — índice extra por (versao_id, depth) p/ filtrar níveis (fases, etc.).
    op.create_index("ix_item_versao_depth", "orcamento_item", ["versao_id", "depth"])


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
