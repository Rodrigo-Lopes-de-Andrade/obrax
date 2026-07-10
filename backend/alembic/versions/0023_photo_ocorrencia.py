"""B8.1 / D8.1 — tabelas photo e ocorrencia (fotos de campo + ocorrências, US-17/US-18).

Fotos capturadas em campo. O app mobile opera offline: cada foto ganha um
`client_photo_id` (UUID gerado no aparelho) que serve de chave de idempotência
no sync — reenviar a mesma foto após queda de rede não cria duplicata. O upload
não passa pela API (presigned PUT direto no storage, como documento); a linha
nasce `pendente` e vira `sincronizado` no confirm.

Decisões de schema (mesmo padrão de documento/ticket):
- `company_id` denormalizado + RLS `tenant_isolation` simples nas duas tabelas.
- `obra_id` NO ACTION (não apaga obra com fotos/ocorrências; o cascade por
  company remove no mesmo statement).
- Dedup em duas dimensões (D8.1): UNIQUE parcial `(company_id, client_photo_id)`
  — a chave do aparelho, idempotência do sync; e índice `(company_id, sha256)`
  — dedup por conteúdo (mesmo arquivo, outro `client_photo_id`).
- `sync_status` enum `photo_sync_status` (pendente/sincronizado): o servidor só
  conhece esses dois estados (uploading é estado do cliente, na fila Dexie).
- `captured_at` = relógio do aparelho (informativo); `synced_at` carimbado pelo
  servidor no confirm. `storage_path` preenchido no confirm (nunca a URL).
- `ocorrencia.status` enum `ocorrencia_status` (aberto/resolvido). GPS opcional
  (`gps_lat`/`gps_lng` NUMERIC(9,6), ~0,1 m). Foto obrigatória é validada na API
  (via `photo.ocorrencia_id`, ligado no POST).
- `photo.ocorrencia_id` FK SET NULL: uma foto pode ser evidência de uma
  ocorrência ou avulsa (galeria). Apagar a ocorrência não apaga a foto.
- Soft delete (`deleted_at`) nas duas — histórico preservado.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE TYPE photo_sync_status AS ENUM ('pendente','sincronizado')")
    op.execute("CREATE TYPE ocorrencia_status AS ENUM ('aberto','resolvido')")

    # ocorrencia primeiro: photo referencia ocorrencia_id.
    op.create_table(
        "ocorrencia",
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
            postgresql.ENUM(name="ocorrencia_status", create_type=False),
            nullable=False,
            server_default=sa.text("'aberto'"),
        ),
        sa.Column("gps_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("gps_lng", sa.Numeric(9, 6), nullable=True),
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
    # Listagem por obra, mais recentes primeiro (id v7 ~ tempo), ignorando removidas.
    op.execute(
        "CREATE INDEX ix_ocorrencia_obra_id_desc ON ocorrencia (obra_id, id DESC) "
        "WHERE deleted_at IS NULL"
    )

    op.create_table(
        "photo",
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
        sa.Column(
            "ocorrencia_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ocorrencia.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Chave do aparelho (idempotência do sync). Gerada no cliente offline.
        sa.Column("client_photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "sync_status",
            postgresql.ENUM(name="photo_sync_status", create_type=False),
            nullable=False,
            server_default=sa.text("'pendente'"),
        ),
        # Relógio do aparelho (quando a foto foi tirada) — informativo.
        sa.Column("captured_at", sa.TIMESTAMP(timezone=True), nullable=False),
        # Chave no bucket, preenchida no confirm (nunca a URL assinada).
        sa.Column("storage_path", sa.Text(), nullable=True),
        # Carimbo do servidor no confirm.
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Dedup por chave do aparelho (idempotência): reenviar o mesmo client_photo_id
    # cai na linha existente. Parcial — soft delete libera a chave.
    op.execute(
        "CREATE UNIQUE INDEX ux_photo_company_client_id "
        "ON photo (company_id, client_photo_id) WHERE deleted_at IS NULL"
    )
    # Dedup por conteúdo (mesmo arquivo com outro client_photo_id).
    op.execute(
        "CREATE INDEX ix_photo_company_sha256 "
        "ON photo (company_id, sha256) WHERE deleted_at IS NULL"
    )
    # Galeria da obra, mais recentes primeiro.
    op.execute(
        "CREATE INDEX ix_photo_obra_id_desc ON photo (obra_id, id DESC) WHERE deleted_at IS NULL"
    )
    # Fotos de uma ocorrência (evidências).
    op.execute(
        "CREATE INDEX ix_photo_ocorrencia ON photo (ocorrencia_id) "
        "WHERE ocorrencia_id IS NOT NULL AND deleted_at IS NULL"
    )

    for table in ("ocorrencia", "photo"):
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
