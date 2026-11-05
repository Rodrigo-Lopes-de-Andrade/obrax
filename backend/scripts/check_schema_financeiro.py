"""Verificação de schema do módulo financeiro (Dicionário §6) — consulta o catálogo.

Confere, para cada tabela do módulo que EXISTE no banco:
  1. RLS habilitada e forçada (relrowsecurity AND relforcerowsecurity);
  2. toda policy com USING e WITH CHECK, e ao menos uma policy por tabela;
  3. GRANT de SELECT, INSERT, UPDATE e DELETE, um a um, a app_user e app_admin;
  3b. USING e WITH CHECK de toda policy são EXATAMENTE a expressão canônica
      `(company_id = app_current_company_id())` (forma de pg_get_expr; Dicionário §2),
      o que também barra `... OR true` e `current_setting` cru;
  4. nenhuma view sem security_invoker (o módulo não cria views — ESPEC §7.4).

Sai com código 1 e mensagem clara se algo faltar. Uso:
    cd backend && uv run python scripts/check_schema_financeiro.py
Conecta com `settings.database_url` (exporte DATABASE_URL local antes).
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

# Permite `python scripts/check_schema_financeiro.py` (sys.path[0] seria scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Extensível: acrescente aqui as tabelas das próximas sprints (Dicionário §5).
# Tabela listada que ainda não existe no banco é ignorada; `OBRIGATORIAS` abaixo
# diz quais DEVEM existir já agora.
TABELAS_MODULO: tuple[str, ...] = (
    "obra_fase",
    "categoria_financeira",
    "despesa",
    "cronograma",
    "cronograma_periodo",
    "cronograma_alocacao",
    "medicao",
    "medicao_item",
    "recebimento",
)
OBRIGATORIAS: tuple[str, ...] = ("obra_fase",)
ROLES_GRANT: tuple[str, ...] = ("app_user", "app_admin")
# Forma normalizada devolvida por pg_get_expr para o template do Dicionário §2.
EXPR_CANONICA = "(company_id = app_current_company_id())"

Q_EXISTENTES = """
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = ANY(%(t)s)
"""
Q_RLS = """
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = ANY(%(t)s)
  AND NOT (c.relrowsecurity AND c.relforcerowsecurity)
"""
Q_POLICY_INCOMPLETA = """
SELECT c.relname, p.polname, p.polqual IS NOT NULL, p.polwithcheck IS NOT NULL
FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid
WHERE c.relname = ANY(%(t)s) AND (p.polqual IS NULL OR p.polwithcheck IS NULL)
"""
Q_SEM_POLICY = """
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = ANY(%(t)s)
  AND NOT EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid)
"""
# Um has_table_privilege POR privilégio: com a lista 'SELECT, INSERT, ...' a função
# devolve true se o role tiver QUALQUER um (GRANT parcial passaria — ERRATA E-06).
PRIVILEGIOS: tuple[str, ...] = ("SELECT", "INSERT", "UPDATE", "DELETE")
Q_GRANT = """
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = ANY(%(t)s)
  AND NOT has_table_privilege(%(role)s, c.oid, %(priv)s)
"""
Q_POLICY_EXPR = """
SELECT c.relname, p.polname,
       COALESCE(pg_get_expr(p.polqual, p.polrelid), ''),
       COALESCE(pg_get_expr(p.polwithcheck, p.polrelid), '')
FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid
WHERE c.relname = ANY(%(t)s)
"""
Q_VIEWS = """
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'v'
  AND COALESCE((SELECT option_value FROM pg_options_to_table(c.reloptions)
                WHERE option_name = 'security_invoker'), 'false') <> 'true'
"""


def verificar(conn: psycopg.Connection) -> list[str]:
    """Devolve a lista de falhas (vazia = schema ok)."""
    erros: list[str] = []
    with conn.cursor() as cur:
        cur.execute(Q_EXISTENTES, {"t": list(TABELAS_MODULO)})
        existentes = sorted(r[0] for r in cur.fetchall())
        for t in OBRIGATORIAS:
            if t not in existentes:
                erros.append(f"{t}: tabela obrigatória não existe")
        if not existentes:
            return erros
        p = {"t": existentes}

        cur.execute(Q_RLS, p)
        for (t,) in cur.fetchall():
            erros.append(f"{t}: RLS não está habilitada E forçada (ENABLE + FORCE)")

        cur.execute(Q_SEM_POLICY, p)
        for (t,) in cur.fetchall():
            erros.append(f"{t}: nenhuma policy (RLS sem policy nega tudo / schema incompleto)")

        cur.execute(Q_POLICY_INCOMPLETA, p)
        for t, pol, using, check in cur.fetchall():
            faltam = [n for n, ok in (("USING", using), ("WITH CHECK", check)) if not ok]
            erros.append(f"{t}: policy {pol} sem {' e '.join(faltam)}")

        cur.execute(Q_POLICY_EXPR, p)
        for t, pol, using, check in cur.fetchall():
            for nome, expr in (("USING", using), ("WITH CHECK", check)):
                if not expr:
                    continue  # ausência já reportada por Q_POLICY_INCOMPLETA
                if expr != EXPR_CANONICA:
                    erros.append(
                        f"{t}: policy {pol} ({nome}) fora do padrão: encontrado "
                        f"{expr!r}, esperado {EXPR_CANONICA!r}"
                    )

        for role in ROLES_GRANT:
            for priv in PRIVILEGIOS:
                cur.execute(Q_GRANT, {**p, "role": role, "priv": priv})
                for (t,) in cur.fetchall():
                    erros.append(f"{t}: falta GRANT {priv} para {role}")

        cur.execute(Q_VIEWS)
        for (v,) in cur.fetchall():
            erros.append(f"view {v}: sem security_invoker=true (vaza RLS — ESPEC §7.4)")
    return erros


def main() -> int:
    from app.core.config import settings

    with psycopg.connect(settings.database_url_raw) as conn:
        erros = verificar(conn)
        with conn.cursor() as cur:
            cur.execute(Q_EXISTENTES, {"t": list(TABELAS_MODULO)})
            existentes = sorted(r[0] for r in cur.fetchall())
    if erros:
        print("FALHA no schema do módulo financeiro:", file=sys.stderr)
        for e in erros:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK — schema financeiro verificado ({', '.join(existentes)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
