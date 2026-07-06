"""D1.2 — enums necessários para companies/users/user_company_role

Enums são criados no Postgres, nunca no Python (ver docs/CLAUDE.md). Os
demais enums do schema completo (obra_status, orcamento_status, etc. — ver
docs/ESPEC.md seção 7) pertencem às tabelas que serão criadas em sprints
futuras e não são criados aqui (mudança cirúrgica: só o que D1.2 precisa).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    op.execute(
        "CREATE TYPE user_role AS ENUM "
        "('owner','admin','gestor','orcamentista','financeiro','viewer','campo','ai')"
    )
    op.execute("CREATE TYPE company_tier AS ENUM ('starter','pro','enterprise')")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
