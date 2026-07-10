"""D9.1 — soft-delete + anonimização LGPD de clientes/users (B9.5, US-21)

Right to be forgotten com retenção legal: nunca apagamos a linha (obrigação de
guarda de ~5 anos); em vez disso **anonimizamos** os dados pessoais (CPF/CNPJ,
nome, e-mail, telefone) depois da janela de 30 dias de soft-delete.

Decisões de schema:
- `anonymized_at TIMESTAMPTZ` em `clientes` e `users`: carimba quando o PII foi
  removido (NULL = ainda íntegro). O "is_active" do SPRINTS já é representado
  pelo `deleted_at IS NULL` existente (soft-delete) — não duplicamos estado.
- `lgpd_anonimizar_cliente(uuid)`: sobrescreve o PII de um cliente e marca
  `anonymized_at`. Idempotente (`anonymized_at IS NULL` no WHERE). O
  `audit_trigger` já anexado a `clientes` (0011) registra o UPDATE em
  `audit_log` — é o tombstone exigido pela US-21.
- `lgpd_anonimizar_expirados()`: anonimiza todos os clientes soft-deletados há
  mais de 30 dias e ainda não anonimizados; devolve a contagem. É a rotina de
  manutenção (roda como `app_admin`/`obrax`, BYPASSRLS — varre todos os tenants)
  que um agendador chamaria; aqui é exercitada direto nos testes.
- `lgpd_anonimizar_user(uuid)`: equivalente para um usuário do sistema (staff).
  `users` não tem `company_id`, então o `audit_trigger` genérico não se aplica —
  a anonimização de usuário fica sem tombstone automático (limitação conhecida;
  o fluxo principal da US-21 é sobre o titular = cliente).

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.add_column(
        "clientes",
        sa.Column("anonymized_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("anonymized_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # A validação de CPF/CNPJ (0012) impede gravar um documento-tombstone. Uma
    # linha anonimizada é, por definição, um marcador — não um documento real —,
    # então isentamos as linhas anonimizadas do CHECK de validade (o documento
    # de linhas ativas continua obrigatoriamente válido).
    op.execute("ALTER TABLE clientes DROP CONSTRAINT ck_clientes_documento_valido")
    op.execute(
        "ALTER TABLE clientes ADD CONSTRAINT ck_clientes_documento_valido "
        "CHECK (anonymized_at IS NOT NULL "
        "       OR fn_validate_documento(tipo_pessoa::text, documento::text)) NOT VALID"
    )
    op.execute("ALTER TABLE clientes VALIDATE CONSTRAINT ck_clientes_documento_valido")

    # Anonimização de um cliente (PII → tombstone). Idempotente. O documento
    # anonimizado deriva do id (único) para não colidir na UNIQUE
    # (company_id, documento). O UPDATE é auditado pelo trigger de clientes.
    op.execute(
        """
        CREATE FUNCTION lgpd_anonimizar_cliente(p_cliente_id uuid) RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
          UPDATE clientes SET
            documento = 'ANON-' || id::text,
            nome = '[titular removido - LGPD]',
            email = NULL,
            telefone = NULL,
            anonymized_at = now()
          WHERE id = p_cliente_id AND anonymized_at IS NULL;
        END;
        $$
        """
    )

    # Rotina de manutenção: anonimiza clientes soft-deletados há >30 dias.
    op.execute(
        """
        CREATE FUNCTION lgpd_anonimizar_expirados() RETURNS integer
        LANGUAGE plpgsql AS $$
        DECLARE
          v_count integer;
        BEGIN
          WITH alvos AS (
            SELECT id FROM clientes
            WHERE deleted_at IS NOT NULL
              AND deleted_at < now() - interval '30 days'
              AND anonymized_at IS NULL
          )
          UPDATE clientes c SET
            documento = 'ANON-' || c.id::text,
            nome = '[titular removido - LGPD]',
            email = NULL,
            telefone = NULL,
            anonymized_at = now()
          FROM alvos WHERE c.id = alvos.id;
          GET DIAGNOSTICS v_count = ROW_COUNT;
          RETURN v_count;
        END;
        $$
        """
    )

    # Anonimização de um usuário do sistema (staff removido por LGPD).
    op.execute(
        """
        CREATE FUNCTION lgpd_anonimizar_user(p_user_id uuid) RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
          UPDATE users SET
            email = 'anon-' || id::text || '@removido.lgpd',
            nome = '[usuário removido - LGPD]',
            password_hash = '',
            deleted_at = COALESCE(deleted_at, now()),
            anonymized_at = now()
          WHERE id = p_user_id AND anonymized_at IS NULL;
        END;
        $$
        """
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
