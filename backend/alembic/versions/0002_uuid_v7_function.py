"""Fundação — função uuid_generate_v7()

Postgres 16 não tem geração nativa de UUIDv7 (isso só chega no core em PG18).
Como o projeto exige IDs UUID v7 ordenáveis (ver docs/CLAUDE.md), criamos uma
função SQL/plpgsql que gera UUIDs versão 7 (RFC 9562) usando `pgcrypto` como
fonte de aleatoriedade, para usar como `server_default` em todo PK das
tabelas de domínio — assim o ID é sempre gerado no banco, mesmo em INSERTs
feitos fora do ORM (seeds, psql manual, etc).

Layout (128 bits):
  48 bits  unix_ts_ms (big-endian)
  4  bits  version (sempre 0111 = 7)
  12 bits  rand_a
  2  bits  variant (sempre 10)
  62 bits  rand_b

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06
"""

from alembic import op

revision = "0002"
down_revision = "0001"
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
    op.execute("COMMENT ON FUNCTION uuid_generate_v7() IS 'Gera UUID v7 (RFC 9562), ordenável por tempo'")
    op.execute("GRANT EXECUTE ON FUNCTION uuid_generate_v7() TO app_user, app_admin")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
