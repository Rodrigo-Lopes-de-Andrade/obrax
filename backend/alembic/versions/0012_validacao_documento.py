"""D2.1 — validação de CPF/CNPJ no Postgres (CHECK + UDFs)

A validação de dígito verificador de CPF/CNPJ já existe na camada de API
(app/modules/gestao/clientes/validators.py, retorna 422). Esta migration a
espelha no banco como defesa em profundidade: qualquer INSERT/UPDATE de
`clientes` — inclusive por psql/seed direto, fora do FastAPI — que grave um
`documento` inválido para o `tipo_pessoa` falha com erro claro.

Decisões:
- Três funções `IMMUTABLE` (dependem só dos argumentos): `fn_validate_cpf` e
  `fn_validate_cnpj` reproduzem exatamente o algoritmo do validators.py
  (mesmos pesos, mesma regra de dígito, rejeitam todos-iguais); a fachada
  `fn_validate_documento(tipo, doc)` roteia por tipo. IMMUTABLE é requisito para
  uso em CHECK constraint.
- Ambas normalizam o documento (só dígitos) antes de validar, então um valor
  formatado ('111.444.777-35') também passa — embora a API sempre grave só
  dígitos.
- CHECK adicionada com `NOT VALID` seguido de `VALIDATE CONSTRAINT`: padrão
  que a disciplina Squawk exige em tabela já existente (evita ACCESS EXCLUSIVE
  longo revalidando linhas sob lock). A tabela está vazia aqui, mas o padrão
  vale para produção.
- Casts explícitos `::text` na expressão do CHECK: `tipo_pessoa` é CHAR(2) e
  `documento` é CITEXT — o cast fixa a resolução para a assinatura (text, text)
  das funções sem depender de cast implícito.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-07
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '3s'")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_validate_cpf(doc text)
        RETURNS boolean
        LANGUAGE plpgsql
        IMMUTABLE
        AS $$
        DECLARE
          digits text := regexp_replace(coalesce(doc, ''), '[^0-9]', '', 'g');
          len    int;
          i      int;
          total  int;
          chk    int;
        BEGIN
          IF length(digits) <> 11 OR digits = repeat(left(digits, 1), 11) THEN
            RETURN false;
          END IF;
          FOREACH len IN ARRAY ARRAY[9, 10] LOOP
            total := 0;
            FOR i IN 0..len - 1 LOOP
              total := total + substr(digits, i + 1, 1)::int * (len + 1 - i);
            END LOOP;
            chk := (total * 10) % 11 % 10;
            IF chk <> substr(digits, len + 1, 1)::int THEN
              RETURN false;
            END IF;
          END LOOP;
          RETURN true;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_validate_cnpj(doc text)
        RETURNS boolean
        LANGUAGE plpgsql
        IMMUTABLE
        AS $$
        DECLARE
          digits  text := regexp_replace(coalesce(doc, ''), '[^0-9]', '', 'g');
          w12     int[] := ARRAY[5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
          w13     int[] := ARRAY[6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
          weights int[];
          len     int;
          i       int;
          total   int;
          rem     int;
          chk     int;
        BEGIN
          IF length(digits) <> 14 OR digits = repeat(left(digits, 1), 14) THEN
            RETURN false;
          END IF;
          FOREACH len IN ARRAY ARRAY[12, 13] LOOP
            weights := CASE WHEN len = 12 THEN w12 ELSE w13 END;
            total := 0;
            FOR i IN 0..len - 1 LOOP
              total := total + substr(digits, i + 1, 1)::int * weights[i + 1];
            END LOOP;
            rem := total % 11;
            chk := CASE WHEN rem < 2 THEN 0 ELSE 11 - rem END;
            IF chk <> substr(digits, len + 1, 1)::int THEN
              RETURN false;
            END IF;
          END LOOP;
          RETURN true;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_validate_documento(tipo text, doc text)
        RETURNS boolean
        LANGUAGE sql
        IMMUTABLE
        AS $$
          SELECT CASE tipo
            WHEN 'PF' THEN fn_validate_cpf(doc)
            WHEN 'PJ' THEN fn_validate_cnpj(doc)
            ELSE false
          END;
        $$;
        """
    )

    for fn in (
        "fn_validate_cpf(text)",
        "fn_validate_cnpj(text)",
        "fn_validate_documento(text, text)",
    ):
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO app_user, app_admin")

    op.execute(
        "COMMENT ON FUNCTION fn_validate_documento(text, text) IS "
        "'Valida CPF (PF) / CNPJ (PJ) por dígito verificador — espelha validators.py'"
    )

    op.execute(
        "ALTER TABLE clientes ADD CONSTRAINT ck_clientes_documento_valido "
        "CHECK (fn_validate_documento(tipo_pessoa::text, documento::text)) NOT VALID"
    )
    op.execute("ALTER TABLE clientes VALIDATE CONSTRAINT ck_clientes_documento_valido")


def downgrade() -> None:
    raise NotImplementedError("migrations são forward-only — ver docs/CLAUDE.md")
