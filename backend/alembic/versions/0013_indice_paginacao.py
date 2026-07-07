"""D2.2 — índice de paginação por cursor em clientes e obras

Validação via EXPLAIN ANALYZE (D2.2) revelou um descasamento: a listagem de
clientes/obras pagina por `ORDER BY id DESC` com cursor em `id` (UUID v7, já
ordenável por tempo), mas os índices de 0009 são `(company_id, created_at DESC)`
— cuja segunda coluna (`created_at`) o planner não aproveita, pois a ordenação é
por `id`. Sem um índice que case a ordenação, o plano vira "pega todas as linhas
do tenant (via prefixo company_id) → Sort por id", que degrada com o tamanho do
tenant.

Este índice parcial `(company_id, id DESC) WHERE deleted_at IS NULL` casa
exatamente o caminho quente (listagem default + cursor): `company_id` como
Index Cond e a ordem por `id DESC` satisfeita pelo próprio índice, com o LIMIT
parando após N linhas — Index (Only) Scan, sem Sort, independente do número de
obras/clientes do tenant. O predicado parcial reflete o `deleted_at IS NULL`
sempre presente na listagem e mantém o índice enxuto (fora os soft-deleted).

Os índices do ESPEC § 7 — `(company_id, status)` e `(company_id, created_at
DESC)` — são mantidos: servem os filtros por status e possíveis relatórios por
data.

`CREATE INDEX CONCURRENTLY` (fora de transação, via autocommit_block): as
tabelas já existem desde 0009, então criar o índice sem lock de escrita é o
padrão que a disciplina Squawk exige para tabela existente.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-07
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_clientes_company_id_desc "
            "ON clientes (company_id, id DESC) WHERE deleted_at IS NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_obras_company_id_desc "
            "ON obras (company_id, id DESC) WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
