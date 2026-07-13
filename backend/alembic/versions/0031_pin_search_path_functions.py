"""Hardening — fixa search_path em funções de validação e LGPD

Mesma classe do fix de `uuid_generate_v7()` na 0028: estas funções chamam outras
funções/tabelas do schema `public` sem qualificar, resolvendo pelo search_path de
quem invoca. Diferença: elas vivem em `public`, que **está** no search_path padrão
do `app_user` (`$user, public`), então NÃO quebram na operação normal da API — só
sob search_path vazio/restrito (ex.: o `COPY` do `pg_restore`, que roda com
`search_path=''`, fez o restore drill falhar em `fn_validate_documento` →
`fn_validate_cpf`).

Fixar `SET search_path` na própria função torna a resolução independente do caller
(defesa em profundidade + simplifica o restore drill, ver RUNBOOK §5). `pg_catalog`
explícito por higiene; `extensions` incluso por consistência com a 0028 (schemas
inexistentes no path são ignorados sem erro).

Alvos:
- fn_validate_cpf(text), fn_validate_cnpj(text), fn_validate_documento(text, text)
- lgpd_anonimizar_cliente(uuid), lgpd_anonimizar_user(uuid), lgpd_anonimizar_expirados()

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-13
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

_FUNCTIONS = (
    "public.fn_validate_cpf(text)",
    "public.fn_validate_cnpj(text)",
    "public.fn_validate_documento(text, text)",
    "public.lgpd_anonimizar_cliente(uuid)",
    "public.lgpd_anonimizar_user(uuid)",
    "public.lgpd_anonimizar_expirados()",
)


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")
    for signature in _FUNCTIONS:
        op.execute(f"ALTER FUNCTION {signature} SET search_path = pg_catalog, public, extensions")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
