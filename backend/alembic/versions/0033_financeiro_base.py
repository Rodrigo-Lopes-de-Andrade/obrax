"""S-F3 — categoria_financeira, despesa e FK composta com tenant (ERRATA E-08)

Cria `categoria_financeira` (Dicionário §4.2) e `despesa` (§4.3), com RLS pelo
template do §2 (ENABLE + FORCE, policy USING/WITH CHECK com
`app_current_company_id()`). O GRANT a `app_user`/`app_admin` vem do
`ALTER DEFAULT PRIVILEGES` da 0001 e é conferido por `scripts/check_schema_financeiro.py`.

Decisão E-08 (2026-11-22): toda FK de tabela do módulo para tabela de tenant é
`(company_id, x_id) -> pai(company_id, id)`, para o banco recusar apontar para linha
de outro tenant (a FK confere o pai sem RLS). Por isso:
  * `UNIQUE (company_id, id)` em `obras`, `obra_fase`, `documento`,
    `orcamento_versao` e `categoria_financeira` (alvo das FKs compostas);
  * `obra_fase.obra_id` e `obra_fase.orcamento_versao_id` trocam a FK simples pela composta;
  * `UNIQUE (obra_id, codigo)` de `obra_fase` vira `(company_id, obra_id, codigo)`, para
    a duplicata de código não servir de oráculo de existência de obra de outro tenant.

Extensão da E-08 (E-11): a despesa aponta para fase e documento da MESMA obra, também no
banco. `UNIQUE (company_id, obra_id, id)` em `obra_fase` e `documento`; as FKs de
`despesa.obra_fase_id` e `despesa.documento_id` passam a ser
`(company_id, obra_id, x_id) -> pai(company_id, obra_id, id)`. Sem isso o banco aceitaria
despesa da obra 1 com fase da obra 2 (mesma empresa) e corromperia o orçado x realizado.
Com `documento_id` nulo a FK (MATCH SIMPLE) não é conferida.

Texto obrigatório não pode ser só espaço: `CHECK (btrim(x) <> '')` em `categoria_financeira.nome`,
`despesa.fornecedor_nome` e `despesa.descricao` (rede do strip feito no service).

Ações de ON DELETE:
  * obra, fase, categoria -> NO ACTION: não se apaga pai com despesa; categoria só se
    desativa (CA-F05.4). O cascade por `company_id` apaga tudo no mesmo statement.
  * `documento_id` e `orcamento_versao_id` -> `ON DELETE SET NULL (<coluna>)` (PG >= 15):
    `SET NULL` sem lista de colunas anularia também `company_id` (NOT NULL) e o DELETE
    do pai falharia. Com a lista, só a coluna do vínculo é anulada.
  * `created_by -> users(id)`: `users` não é tabela de tenant (não tem company_id), FK
    simples, SET NULL (o usuário pode ser removido).

Auditoria: `audit_despesa` (E-11) usa o `audit_trigger()` genérico da 0011.

Índices em tabela existente: `CREATE UNIQUE INDEX CONCURRENTLY` em `autocommit_block`
(padrão Squawk, como a 0013) + `ADD CONSTRAINT ... UNIQUE USING INDEX`; FK nova em
tabela existente com `NOT VALID` + `VALIDATE CONSTRAINT`. Forward-only.

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

# (tabela, nome da constraint) — UNIQUE (company_id, id) em tabelas já existentes.
_PAIS_EXISTENTES = (
    ("obras", "uq_obras_company_id"),
    ("obra_fase", "uq_obra_fase_company_id"),
    ("documento", "uq_documento_company_id"),
    ("orcamento_versao", "uq_orcamento_versao_company_id"),
)


def _tenant_policy(tabela: str) -> None:
    op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {tabela}_tenant_isolation ON {tabela}
          USING (company_id = app_current_company_id())
          WITH CHECK (company_id = app_current_company_id())
        """
    )


def upgrade() -> None:
    # 1. Índices únicos concorrentes (fora de transação). O SET LOCAL não sobrevive
    #    ao autocommit_block; aqui vale o SET de sessão, restaurado ao final.
    with op.get_context().autocommit_block():
        op.execute("SET lock_timeout = '3s'")
        for tabela, nome in _PAIS_EXISTENTES:
            op.execute(
                f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {nome} "
                f"ON {tabela} (company_id, id)"
            )
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_obra_fase_company_obra_codigo "
            "ON obra_fase (company_id, obra_id, codigo)"
        )
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_obra_fase_company_obra_id "
            "ON obra_fase (company_id, obra_id, id)"
        )
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_documento_company_obra_id "
            "ON documento (company_id, obra_id, id)"
        )
        op.execute("RESET lock_timeout")

    op.execute("SET LOCAL lock_timeout = '3s'")

    # 2. Promove os índices a constraints (alvo das FKs compostas).
    for tabela, nome in _PAIS_EXISTENTES:
        op.execute(f"ALTER TABLE {tabela} ADD CONSTRAINT {nome} UNIQUE USING INDEX {nome}")
    op.execute(
        "ALTER TABLE obra_fase ADD CONSTRAINT uq_obra_fase_company_obra_codigo "
        "UNIQUE USING INDEX uq_obra_fase_company_obra_codigo"
    )
    op.execute("ALTER TABLE obra_fase DROP CONSTRAINT uq_obra_fase_obra_codigo")
    op.execute(
        "ALTER TABLE obra_fase ADD CONSTRAINT uq_obra_fase_company_obra_id "
        "UNIQUE USING INDEX uq_obra_fase_company_obra_id"
    )
    op.execute(
        "ALTER TABLE documento ADD CONSTRAINT uq_documento_company_obra_id "
        "UNIQUE USING INDEX uq_documento_company_obra_id"
    )

    # 3. obra_fase: FKs simples -> compostas.
    op.execute("ALTER TABLE obra_fase DROP CONSTRAINT obra_fase_obra_id_fkey")
    op.execute("ALTER TABLE obra_fase DROP CONSTRAINT obra_fase_orcamento_versao_id_fkey")
    op.execute(
        "ALTER TABLE obra_fase ADD CONSTRAINT fk_obra_fase_obra "
        "FOREIGN KEY (company_id, obra_id) REFERENCES obras (company_id, id) NOT VALID"
    )
    op.execute(
        "ALTER TABLE obra_fase ADD CONSTRAINT fk_obra_fase_orcamento_versao "
        "FOREIGN KEY (company_id, orcamento_versao_id) "
        "REFERENCES orcamento_versao (company_id, id) "
        "ON DELETE SET NULL (orcamento_versao_id) NOT VALID"
    )
    op.execute("ALTER TABLE obra_fase VALIDATE CONSTRAINT fk_obra_fase_obra")
    op.execute("ALTER TABLE obra_fase VALIDATE CONSTRAINT fk_obra_fase_orcamento_versao")

    # 4. categoria_financeira (Dicionário §4.2)
    op.create_table(
        "categoria_financeira",
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
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("company_id", "id", name="uq_categoria_financeira_company_id"),
        sa.CheckConstraint("btrim(nome) <> ''", name="ck_categoria_nome_nao_vazio"),
    )
    # Índice (não constraint): tem expressão e predicado (Dicionário §1). Alvo do
    # seed idempotente: ON CONFLICT (company_id, lower(nome)) WHERE deleted_at IS NULL.
    op.create_index(
        "uq_categoria_company_nome",
        "categoria_financeira",
        [sa.text("company_id"), sa.text("lower(nome)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    _tenant_policy("categoria_financeira")

    # 5. despesa (Dicionário §4.3)
    op.execute("CREATE TYPE despesa_status AS ENUM ('prevista','paga','cancelada')")
    op.create_table(
        "despesa",
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
        sa.Column("obra_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("obra_fase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fornecedor_nome", sa.Text(), nullable=False),
        sa.Column("fornecedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("valor", sa.Numeric(18, 2), nullable=False),
        sa.Column("data_competencia", sa.Date(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "prevista", "paga", "cancelada", name="despesa_status", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grupo_parcelas_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parcela_num", sa.SmallInteger(), nullable=True),
        sa.Column("parcela_total", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("valor > 0", name="ck_despesa_valor_positivo"),
        sa.CheckConstraint("btrim(fornecedor_nome) <> ''", name="ck_despesa_fornecedor_nao_vazio"),
        sa.CheckConstraint("btrim(descricao) <> ''", name="ck_despesa_descricao_nao_vazia"),
        sa.CheckConstraint(
            "(status = 'paga') = (data_pagamento IS NOT NULL)", name="ck_despesa_pago_com_data"
        ),
        sa.CheckConstraint(
            "(parcela_num IS NULL) = (parcela_total IS NULL)", name="ck_despesa_parcela_par"
        ),
        sa.CheckConstraint(
            "parcela_num IS NULL OR (parcela_num >= 1 AND parcela_num <= parcela_total)",
            name="ck_despesa_parcela_faixa",
        ),
        sa.CheckConstraint(
            "grupo_parcelas_id IS NOT NULL OR parcela_num IS NULL",
            name="ck_despesa_parcela_grupo",
        ),
    )
    # FKs compostas com company_id (E-08). Tabela nova e vazia: sem NOT VALID.
    op.execute(
        "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_obra "
        "FOREIGN KEY (company_id, obra_id) REFERENCES obras (company_id, id)"
    )
    op.execute(
        "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_obra_fase "
        "FOREIGN KEY (company_id, obra_id, obra_fase_id) "
        "REFERENCES obra_fase (company_id, obra_id, id)"
    )
    op.execute(
        "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_categoria "
        "FOREIGN KEY (company_id, categoria_id) REFERENCES categoria_financeira (company_id, id)"
    )
    op.execute(
        "ALTER TABLE despesa ADD CONSTRAINT fk_despesa_documento "
        "FOREIGN KEY (company_id, obra_id, documento_id) "
        "REFERENCES documento (company_id, obra_id, id) "
        "ON DELETE SET NULL (documento_id)"
    )

    op.create_index(
        "ix_despesa_realizado",
        "despesa",
        ["company_id", "obra_id", "obra_fase_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_despesa_vencimento",
        "despesa",
        ["company_id", "vencimento"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_despesa_company_id_desc",
        "despesa",
        ["company_id", sa.text("id DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_despesa_grupo_parcelas",
        "despesa",
        ["grupo_parcelas_id"],
        postgresql_where=sa.text("grupo_parcelas_id IS NOT NULL"),
    )
    _tenant_policy("despesa")

    # Auditoria (SEC-F07, CA-F09.4): trigger genérico da 0011, como clientes, obras,
    # documento e orcamento. Grava action='UPDATE' para qualquer mudança (pagar,
    # estornar, cancelar, editar); o que distingue é o diff before/after.
    op.execute(
        "CREATE TRIGGER audit_despesa "
        "AFTER INSERT OR UPDATE OR DELETE ON despesa "
        "FOR EACH ROW EXECUTE FUNCTION audit_trigger()"
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
