"""B2.1 — tabelas clientes e obras (Módulo 1: Gestão de Obras)

Schema conforme docs/ESPEC.md § 7. Ambas têm `company_id` (dado de domínio),
então seguem o padrão multi-tenant das demais tabelas — a RLS vem na migration
seguinte (0010), espelhando a separação tabelas (0004) → policies (0005) do D1.

Decisões de schema:
- `clientes.tipo_pessoa CHAR(2)` com CHECK ('PF','PJ') — documenta e trava o
  domínio do campo já no banco (o ESPEC define CHAR(2); os únicos valores
  válidos são PF/PJ).
- UNIQUE (company_id, documento) em clientes: CPF/CNPJ é único dentro de cada
  empresa (não globalmente — a mesma pessoa pode ser cliente de duas
  construtoras distintas no SaaS).
- `obras.status` default 'planejamento' (estado inicial de uma obra recém
  criada). Validação de transições/datas é da camada de API (B2.3).
- Datas (`data_inicio`, `data_prevista_fim`, `data_real_fim`) são nullable: uma
  obra em planejamento pode ainda não ter datas definidas.
- `valor_contrato NUMERIC(18,2)`: valores monetários nunca em float
  (docs/CLAUDE.md > Precisão financeira).

Índices (docs/ESPEC.md § 7 "Índices Críticos"): (company_id, status),
(company_id, created_at DESC) e (company_id, cliente_id) para o filtro
`GET /obras?cliente_id=`.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute(
        "CREATE TYPE obra_status AS ENUM "
        "('planejamento','execucao','pausada','concluida','cancelada')"
    )

    op.create_table(
        "clientes",
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
        sa.Column("tipo_pessoa", sa.CHAR(2), nullable=False),
        sa.Column("documento", postgresql.CITEXT(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("telefone", sa.Text(), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("tipo_pessoa IN ('PF','PJ')", name="ck_clientes_tipo_pessoa"),
        sa.UniqueConstraint("company_id", "documento", name="uq_clientes_company_documento"),
    )
    op.execute(
        "CREATE INDEX ix_clientes_company_created_at ON clientes (company_id, created_at DESC)"
    )

    op.create_table(
        "obras",
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
        # NO ACTION (default): impede deletar um cliente que ainda tem obras
        # (checado no fim do statement), mas permite o cascade quando a própria
        # empresa é removida (clientes + obras caem juntos na mesma operação).
        sa.Column(
            "cliente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="obra_status", create_type=False),
            nullable=False,
            server_default=sa.text("'planejamento'"),
        ),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_prevista_fim", sa.Date(), nullable=True),
        sa.Column("data_real_fim", sa.Date(), nullable=True),
        sa.Column("valor_contrato", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_obras_company_status", "obras", ["company_id", "status"])
    op.create_index("ix_obras_company_cliente_id", "obras", ["company_id", "cliente_id"])
    op.execute("CREATE INDEX ix_obras_company_created_at ON obras (company_id, created_at DESC)")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
