"""D1.2 — RLS ativa e forçada em companies, users, user_company_role

Padrão (docs/ESPEC.md seção 3): TenantMiddleware faz `SET LOCAL
app.company_id = '<uuid>'` a cada request; toda tabela de domínio tem uma
policy que filtra por esse setting. `FORCE ROW LEVEL SECURITY` garante que
mesmo o dono da tabela (quem rodou a migration) fica sujeito às policies —
só um role com BYPASSRLS (ex.: app_admin, ou o superuser usado para
migrations) escapa disso.

- companies: a própria linha é o tenant, então a policy compara `id`.
- user_company_role: tem `company_id` direto.
- users: tabela de identidade global (não tem `company_id` próprio — um
  usuário pode, em tese, pertencer a mais de uma empresa via
  user_company_role). Isolamento via EXISTS contra user_company_role.
  Premissa: o INSERT em `users` é liberado sem restrição de tenant (`WITH
  CHECK (true)`) porque o fluxo de convite/signup precisa criar a linha de
  `users` *antes* de existir o vínculo em `user_company_role` (ordem:
  INSERT users → INSERT user_company_role, na mesma transação); a linha
  fica invisível para qualquer tenant até o vínculo ser criado, e updates/
  deletes continuam exigindo o vínculo.

`current_setting('app.company_id', true)` com o segundo argumento `true`
retorna NULL (em vez de lançar erro) quando a GUC não foi setada — o que
faz a comparação falhar e nenhuma linha ficar visível (fail-closed por
padrão para uma sessão sem tenant definido).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-06
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_USERS_TENANT_EXISTS = """
    EXISTS (
      SELECT 1 FROM user_company_role ucr
      WHERE ucr.user_id = users.id
        AND ucr.company_id = current_setting('app.company_id', true)::uuid
    )
"""


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    # ---- companies ---------------------------------------------------
    op.execute("ALTER TABLE companies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE companies FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY companies_tenant_isolation ON companies
          USING (id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (id = current_setting('app.company_id', true)::uuid)
        """
    )

    # ---- user_company_role --------------------------------------------
    op.execute("ALTER TABLE user_company_role ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_company_role FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_company_role_tenant_isolation ON user_company_role
          USING (company_id = current_setting('app.company_id', true)::uuid)
          WITH CHECK (company_id = current_setting('app.company_id', true)::uuid)
        """
    )

    # ---- users ----------------------------------------------------------
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY users_tenant_select ON users
          FOR SELECT
          USING ({_USERS_TENANT_EXISTS})
        """
    )
    op.execute(
        f"""
        CREATE POLICY users_tenant_update ON users
          FOR UPDATE
          USING ({_USERS_TENANT_EXISTS})
          WITH CHECK ({_USERS_TENANT_EXISTS})
        """
    )
    op.execute(
        f"""
        CREATE POLICY users_tenant_delete ON users
          FOR DELETE
          USING ({_USERS_TENANT_EXISTS})
        """
    )
    op.execute(
        """
        CREATE POLICY users_tenant_insert ON users
          FOR INSERT
          WITH CHECK (true)
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
