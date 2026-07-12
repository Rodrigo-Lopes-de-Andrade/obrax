"""Fundação — USAGE em `extensions` para os roles de aplicação

Complemento da 0028. Ter `extensions` no search_path de `uuid_generate_v7()` não
basta: sem privilégio USAGE no schema, os objetos ali ficam invisíveis para o
role e o Postgres reporta `function gen_random_bytes(integer) does not exist`.

No Supabase, pgcrypto/citext/pg_trgm são instaladas no schema `extensions`, e a
0001 só concedeu USAGE em `public` a `app_user`/`app_admin`. Toda escrita
autenticada (INSERT via `app_user`) dispara o `server_default = uuid_generate_v7()`
→ `gen_random_bytes` → precisava de USAGE em `extensions`. Idem para o tipo
`citext` e os operadores de `pg_trgm` usados em runtime.

No-op em Postgres local, onde o schema `extensions` não existe (as extensions
vivem em `public`, já coberto pela 0001) — daí o guard por existência.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-12
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'extensions') THEN
            GRANT USAGE ON SCHEMA extensions TO app_user, app_admin;
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
