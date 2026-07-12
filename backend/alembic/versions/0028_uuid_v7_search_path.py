"""Fundação — fixa search_path em uuid_generate_v7()

`uuid_generate_v7()` (migration 0002) chama `gen_random_bytes` (pgcrypto) sem
qualificar o schema, resolvendo pelo search_path de quem invoca. Em Postgres
local isso funciona porque `pgcrypto` é instalada em `public` (no search_path
padrão). No Supabase, porém, as extensions ficam no schema `extensions`, que só
está no search_path do role `postgres` — **não** dos roles de aplicação
`app_user`/`app_admin` (rolconfig vazio, search_path padrão `$user, public`).

Consequência: todo INSERT via `app_user` (toda escrita autenticada da API)
dispara o `server_default = uuid_generate_v7()` e falhava em staging/prod com
`function gen_random_bytes(integer) does not exist`. Leituras não exercitavam a
função, então o smoke de GET não pegou.

Correção (parte 1 de 2 — a 0029 completa com o GRANT de USAGE em `extensions`):
fixar `SET search_path` na própria função incluindo `public` (dev local) e
`extensions` (Supabase). `pg_catalog` explícito por higiene. Schemas
inexistentes no path são ignorados sem erro, então a mesma definição vale nos
dois ambientes.

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-12
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION uuid_generate_v7()
        RETURNS uuid
        LANGUAGE plpgsql
        VOLATILE
        SET search_path = pg_catalog, public, extensions
        AS $$
        DECLARE
          ts_ms      bigint;
          ts_bytes   bytea;
          rand_bytes bytea;
          uuid_bytes bytea;
        BEGIN
          ts_ms := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
          -- int8send devolve 8 bytes big-endian; os 2 primeiros bytes (bits
          -- mais altos) são descartados pois ts_ms cabe em 48 bits até o ano
          -- ~10889.
          ts_bytes := substring(int8send(ts_ms) FROM 3 FOR 6);
          rand_bytes := gen_random_bytes(10);

          uuid_bytes :=
            ts_bytes
            -- byte 6: nibble alto fixo em 0111 (versão 7), nibble baixo aleatório
            || set_byte(substring(rand_bytes FROM 1 FOR 1), 0, (get_byte(rand_bytes, 0) & 15) | 112)
            -- byte 7: rand_a (parte baixa), 8 bits aleatórios
            || substring(rand_bytes FROM 2 FOR 1)
            -- byte 8: 2 bits altos fixos em 10 (variant RFC 4122), 6 bits aleatórios
            || set_byte(substring(rand_bytes FROM 3 FOR 1), 0, (get_byte(rand_bytes, 2) & 63) | 128)
            -- bytes 9-15: rand_b, 56 bits aleatórios
            || substring(rand_bytes FROM 4 FOR 7);

          RETURN encode(uuid_bytes, 'hex')::uuid;
        END;
        $$;
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
