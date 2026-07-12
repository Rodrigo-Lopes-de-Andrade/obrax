"""Hardening RLS — fail-closed com `app.company_id` vazio ('')

Bug de fail-closed exposto ao rodar a suíte atrás de um pooler (Supabase/pgbouncer):
as policies comparavam `company_id = current_setting('app.company_id', true)::uuid`
**sem** `NULLIF`. Numa conexão nova o GUC é indefinido e `current_setting(...,true)`
devolve NULL → `NULL::uuid` = NULL → a linha não casa → retorna nada (fail-closed
correto). Mas depois que **qualquer** transação faz `SET LOCAL app.company_id`, o
valor de *reset* da sessão passa a ser `''` (string vazia, não "indefinido"). Numa
próxima query sem tenant setado, `current_setting('app.company_id', true)` devolve
`''` e `''::uuid` **levanta erro** (`invalid input syntax for type uuid: ""`) em vez
de retornar vazio. Localmente cada teste usa conexão nova (nunca vê o ''), mas atrás
do pooler o backend é reusado e o '' vaza entre testes — daí a flakiness.

Correção (defesa em profundidade, além de destravar os testes): RLS deve
fail-closed (retornar nada), nunca dar erro, quando o contexto de tenant está
ausente OU vazio. Introduz o helper `app_current_company_id()` que faz
`NULLIF(current_setting('app.company_id', true), '')::uuid` (mesmo padrão que o
trigger de audit_log da 0011 já usava) e reescreve todas as 26 policies para
usá-lo no lugar do cast cru.

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-12
"""

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

# Tabelas com a policy uniforme `<policy>_tenant_isolation` (cmd ALL) cujo
# predicado é `company_id = <tenant>` tanto em USING quanto em WITH CHECK.
_UNIFORM_TABLES = [
    "agent_interaction",
    "agent_message",
    "ai_permission",
    "audit_log",
    "checklist_item",
    "clientes",
    "documento",
    "invitations",
    "lgpd_request",
    "obra_membro",
    "obras",
    "ocorrencia",
    "orcamento",
    "orcamento_aprovacao",
    "orcamento_item",
    "orcamento_versao",
    "photo",
    "ticket",
    "ticket_mensagem",
    "user_company_role",
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    # Helper central: '' e ausência ambos viram NULL (fail-closed, sem erro de cast).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_company_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SET search_path = pg_catalog, public
        AS $$
          SELECT NULLIF(current_setting('app.company_id', true), '')::uuid
        $$
        """
    )
    op.execute(
        "COMMENT ON FUNCTION app_current_company_id() IS "
        "'Tenant atual do GUC app.company_id; '''' e ausência viram NULL (RLS fail-closed)'"
    )
    op.execute("GRANT EXECUTE ON FUNCTION app_current_company_id() TO app_user, app_admin")

    # 20 tabelas com predicado uniforme company_id = tenant (USING + WITH CHECK).
    for table in _UNIFORM_TABLES:
        op.execute(
            f"ALTER POLICY {table}_tenant_isolation ON {table} "
            f"USING (company_id = app_current_company_id()) "
            f"WITH CHECK (company_id = app_current_company_id())"
        )

    # companies: o discriminador é a própria PK `id`, não `company_id`.
    op.execute(
        "ALTER POLICY companies_tenant_isolation ON companies "
        "USING (id = app_current_company_id()) "
        "WITH CHECK (id = app_current_company_id())"
    )

    # insumo: catálogo global (company_id IS NULL) visível a todos + os do tenant.
    op.execute(
        "ALTER POLICY insumo_read ON insumo "
        "USING (company_id IS NULL OR company_id = app_current_company_id())"
    )
    op.execute(
        "ALTER POLICY insumo_write ON insumo "
        "USING (company_id = app_current_company_id()) "
        "WITH CHECK (company_id = app_current_company_id())"
    )

    # users: isolamento via join em user_company_role (não tem company_id direto).
    op.execute(
        "ALTER POLICY users_tenant_select ON users "
        "USING (EXISTS (SELECT 1 FROM user_company_role ucr "
        "WHERE ucr.user_id = users.id AND ucr.company_id = app_current_company_id()))"
    )
    op.execute(
        "ALTER POLICY users_tenant_update ON users "
        "USING (EXISTS (SELECT 1 FROM user_company_role ucr "
        "WHERE ucr.user_id = users.id AND ucr.company_id = app_current_company_id())) "
        "WITH CHECK (EXISTS (SELECT 1 FROM user_company_role ucr "
        "WHERE ucr.user_id = users.id AND ucr.company_id = app_current_company_id()))"
    )
    op.execute(
        "ALTER POLICY users_tenant_delete ON users "
        "USING (EXISTS (SELECT 1 FROM user_company_role ucr "
        "WHERE ucr.user_id = users.id AND ucr.company_id = app_current_company_id()))"
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
