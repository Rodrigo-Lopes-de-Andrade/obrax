"""D3.2 — trigger de auditoria em documento (mudança de visibilidade e demais mutações)

Anexa o `audit_trigger()` genérico (criado na 0011) à tabela `documento`. Como
`documento` tem `id` + `company_id`, o trigger serve sem alteração — cada
INSERT/UPDATE/DELETE grava em `audit_log` com `before`/`after` JSONB, `actor_id`
e `ip` (das GUCs de request), igual a clientes/obras.

Atende o requisito do docs/ESPEC.md ("audit_log obrigatório em ... alteração
visibilidade documento"): o toggle de `visivel_cliente` (US-06) é um UPDATE, então
fica registrado com o valor antes/depois. Auditar toda mutação (não só a
visibilidade) é superset do exigido e mantém a consistência com as outras tabelas
de domínio.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-09
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    op.execute(
        "CREATE TRIGGER audit_documento "
        "AFTER INSERT OR UPDATE OR DELETE ON documento "
        "FOR EACH ROW EXECUTE FUNCTION audit_trigger()"
    )


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
