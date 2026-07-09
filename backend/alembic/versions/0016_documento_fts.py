"""D3.1 — índice GIN full-text em documento (busca por nome + OCR)

Suporta a busca textual do GED (B3.4, US-04): `to_tsvector('portuguese', nome ||
ocr_text)` casado com `plainto_tsquery` no endpoint de listagem
(docs/ESPEC.md § 7). A expressão é IMMUTABLE (config `regconfig` constante), então
pode indexar.

`translate(nome, '._-/', '    ')`: separadores de nome de arquivo viram espaço
antes do parser, senão "planta.pdf" vira um único token (tipo `host`/`file`) e
"planta" não casa. A mesma expressão é usada na query (senão o índice não é
aproveitado) — ver documentos/service.py `list_documentos`.

`CREATE INDEX CONCURRENTLY` fora de transação (autocommit_block): a tabela já
existe desde 0014, então cria-se o índice sem lock de escrita — o padrão Squawk
para tabela existente (igual à 0013). Índice parcial `WHERE deleted_at IS NULL`:
casa o predicado sempre presente na listagem e mantém o índice enxuto.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-09
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_documento_fts "
            "ON documento USING GIN "
            "(to_tsvector('portuguese', "
            " translate(nome, '._-/', '    ') || ' ' || coalesce(ocr_text, ''))) "
            "WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
