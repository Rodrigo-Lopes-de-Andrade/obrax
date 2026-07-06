"""D1.1 — extensions e roles (fundação do banco)

Ativa as extensions necessárias ao schema multi-tenant (pgcrypto para
`gen_random_bytes`/`gen_random_uuid`, pg_trgm para busca fuzzy, citext para
colunas case-insensitive como email/cnpj) e cria os dois roles de aplicação:

- app_user: role de runtime usada pelo backend (FastAPI). Sujeita a RLS
  (sem BYPASSRLS, sem superuser) — é o role que a TenantMiddleware assume.
- app_admin: role administrativa para operações cross-tenant (onboarding de
  nova empresa, scripts de seed/manutenção, jobs em background). Tem
  BYPASSRLS porque precisa operar antes de existir um `app.company_id` (ex.:
  criar a primeira linha de `companies`) ou através de múltiplos tenants.

Premissa (ver relatório do agente): as senhas abaixo são credenciais de
desenvolvimento local, no mesmo espírito do `docker-compose.yml` (usuário
`obrax`/senha `obrax`, comentado como "throwaway de dev"). Em staging/prod
essas credenciais serão substituídas via secrets manager (Doppler/Infisical)
no Estágio B/DevOps — nunca reaproveitar este valor fora do Postgres local.

Revision ID: 0001
Revises:
Create Date: 2026-07-06
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_APP_USER_PASSWORD = "app_user_dev_only"
_APP_ADMIN_PASSWORD = "app_admin_dev_only"


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user LOGIN PASSWORD '{_APP_USER_PASSWORD}';
          END IF;
        END
        $$;
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
            CREATE ROLE app_admin LOGIN PASSWORD '{_APP_ADMIN_PASSWORD}' BYPASSRLS;
          END IF;
        END
        $$;
        """
    )

    op.execute("GRANT USAGE ON SCHEMA public TO app_user, app_admin")

    # Default privileges: qualquer tabela criada a partir de agora (por quem
    # rodar as migrations) já concede DML a app_user/app_admin automaticamente,
    # para não precisarmos repetir GRANTs a cada nova tabela de domínio nas
    # próximas sprints.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user, app_admin"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_user, app_admin"
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
