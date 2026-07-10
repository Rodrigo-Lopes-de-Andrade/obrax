"""B6.3 — orcamento_versao.pdf_url → pdf_storage_path (US-17).

Regra do projeto (docs/CLAUDE.md): anexos são **storage paths, nunca URLs** —
uma URL assinada é efêmera (TTL curto) e nunca deve ser persistida. A coluna
nasceu como `pdf_url` em 0019; renomeia para `pdf_storage_path`, deixando
explícito que o valor guardado é a *chave* do objeto no bucket — a URL de
download é assinada sob demanda no GET (TTL 1h). Forward-only.
"""

from __future__ import annotations

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("orcamento_versao", "pdf_url", new_column_name="pdf_storage_path")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
