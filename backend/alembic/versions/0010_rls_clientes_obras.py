"""B2.1 — RLS ativa e forçada em clientes e obras

Ambas têm `company_id` direto, então usam a policy de isolamento simples
(mesmo padrão de `user_company_role`/`invitations`): a sessão só enxerga as
linhas cujo `company_id` bate com `current_setting('app.company_id')`, setado
por request pela TenantMiddleware/`get_db` (docs/ESPEC.md § 3).

`FORCE ROW LEVEL SECURITY` sujeita até o dono da tabela às policies; só roles
com BYPASSRLS (app_admin, superuser das migrations) escapam. O segundo
argumento `true` de `current_setting` retorna NULL quando a GUC não foi setada
→ comparação falha → nenhuma linha visível (fail-closed).

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-06
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    for table in ("clientes", "obras"):
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
