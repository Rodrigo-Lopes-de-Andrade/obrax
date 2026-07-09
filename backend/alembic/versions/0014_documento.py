"""B3.1 — tabela `documento` + RLS (Módulo 1: GED)

Schema conforme docs/ESPEC.md § 7 (que nomeia a tabela no singular `documento`,
ao contrário de clientes/obras no plural — seguimos o nome explícito do ESPEC).
Tem `company_id` (dado de domínio), então adota o mesmo padrão multi-tenant das
demais tabelas: RLS de isolamento por `company_id` já nesta migration (o GED não
tem a separação tabela→policy que o D1 fez; RLS entra junto, como em audit_log).

Decisões de schema:
- `obra_id` FK com NO ACTION (default): impede apagar uma obra que ainda tem
  documentos, mas o cascade por company continua funcionando — ao remover a
  company, os documentos caem via `company_id ON DELETE CASCADE` no mesmo
  statement (mesma mecânica de obras→clientes na 0009).
- Colunas do ciclo de upload são NULLABLE (`storage_path`, `size_bytes`,
  `sha256`, `ocr_text`): a linha nasce no POST /documentos e só ganha o hash/
  tamanho no POST /documentos/confirm (B3.2/B3.3). `categoria` idem — a
  obrigatoriedade de categorizar é validação de API, não do schema.
- `uploaded_by` FK users com ON DELETE SET NULL: o documento sobrevive à
  remoção (física/LGPD) de quem o enviou.
- `UNIQUE (obra_id, sha256)`: dedup por conteúdo dentro da mesma obra
  (docs/ESPEC.md § 7). Com `sha256` NULL, o Postgres trata cada linha como
  distinta — várias pendências pré-confirm convivem; a unicidade só morde
  quando o hash é preenchido no confirm.

Fora do escopo desta task (ficam nas tasks de banco da S3):
- Índice GIN full-text `to_tsvector(nome || ocr_text)` → D3.1.
- Trigger de auditoria de `visivel_cliente` → D3.2 (o `audit_trigger()` genérico
  da 0011 já serve; só falta anexá-lo).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute(
        "CREATE TYPE documento_tipo AS ENUM ('projeto','contrato','nota_fiscal','foto','outro')"
    )

    op.create_table(
        "documento",
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
        # NO ACTION (default): não deixa apagar obra com documentos; o cascade
        # por company remove os documentos no mesmo statement (ver docstring).
        sa.Column(
            "obra_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obras.id"),
            nullable=False,
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column(
            "tipo",
            postgresql.ENUM(name="documento_tipo", create_type=False),
            nullable=False,
        ),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.CHAR(64), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column(
            "visivel_cliente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # SET NULL: documento sobrevive à remoção do usuário que fez o upload.
        sa.Column(
            "uploaded_by",
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
        sa.UniqueConstraint("obra_id", "sha256", name="uq_documento_obra_sha256"),
    )
    op.create_index("ix_documento_obra_categoria", "documento", ["obra_id", "categoria"])

    # RLS: mesmo padrão tenant_isolation das demais tabelas com company_id
    # (fail-closed sem `app.company_id`; FORCE sujeita até o dono às policies).
    op.execute("ALTER TABLE documento ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documento FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY documento_tenant_isolation ON documento
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
