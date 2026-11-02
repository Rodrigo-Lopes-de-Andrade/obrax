# Dicionário de Dados — Módulos 5 e 6

**Versão:** 1.0 | **Data:** 2026-11-02
**Consome:** [ESPEC do módulo](ESPEC.md)
**Base verificada:** schema do `main` em `89593a5` — última migration aplicada: `0031`

Este documento é a fonte de verdade **semântica**: o que cada coluna significa e o que a viola.
Tipos e constraints existem para impedir estado impossível; onde a regra não cabe no banco, a
coluna diz quem a garante.

---

## 1. Convenções do projeto

Valem para todas as tabelas abaixo. A exceção, quando houver, está marcada na tabela.

| Item | Convenção |
|---|---|
| PK | `id UUID PRIMARY KEY DEFAULT uuid_generate_v7()` — ordenável no tempo, serve de cursor |
| Tenant | `company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE` |
| Criação | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` |
| Autor | `created_by UUID NULL REFERENCES users(id)` — nullable porque o usuário pode ser removido |
| Soft delete | `deleted_at TIMESTAMPTZ NULL`. Toda listagem filtra `IS NULL` |
| FK para `obras` | `ON DELETE NO ACTION` — não se apaga obra com movimento financeiro. O cascade por `company_id` remove tudo no mesmo statement |
| Valores monetários | `NUMERIC(18,2)`. **Nunca** `float`, `real` ou `double precision` |
| Percentuais | `NUMERIC(7,4)` como **fração**: `0.1500` = 15%. Conversão para exibição é da apresentação |
| Enums | criados no Postgres, nunca em Python. Alterar em produção exige migration expand-contract |
| Migration | começa com `SET LOCAL lock_timeout = '3s'`; índice em tabela existente é `CREATE INDEX CONCURRENTLY` em `autocommit_block()` |
| Paginação | índice `(company_id, id DESC) WHERE deleted_at IS NULL` nas tabelas listáveis |

### Unique com coluna nullable

`UNIQUE` no Postgres trata `NULL` como distinto: dois registros com `NULL` na mesma coluna
**não** colidem. Onde a unicidade precisa valer apesar do nullable, o dicionário especifica
índice único **parcial** com o predicado explícito.

### Unicidade parcial ou sobre expressão é ÍNDICE, não constraint

**Verificado executando:** `UNIQUE (company_id, lower(nome)) WHERE deleted_at IS NULL` dentro de
`CREATE TABLE` é **erro de sintaxe** — `ERROR: syntax error at or near "("`. Restrição de
unicidade no Postgres não aceita `WHERE` nem expressão.

Toda unicidade com predicado ou com função vai como `CREATE UNIQUE INDEX`, fora do
`create_table`. É um erro que só aparece quando a migration roda, ou seja, depois de a sprint
parecer pronta.

```python
# ✅ correto
op.create_index("uq_categoria_company_nome", "categoria_financeira",
                [sa.text("company_id"), sa.text("lower(nome)")],
                unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
```

---

## 2. Template de tabela nova — copiar este, não uma migration antiga

> ⚠️ **Não copie o bloco de RLS da migration 0023 ou anterior.** Elas usam
> `current_setting('app.company_id', true)::uuid` cru no predicado, padrão que a migration 0030
> substituiu nas 26 policies existentes.
>
> **Medido:** com `app.company_id` vazio (string `''`), o cast cru **não vaza** — levanta
> `ERROR: invalid input syntax for type uuid: ""`, e o request morre com 500. É fail-closed,
> porém quebrado. O helper transforma isso em negação limpa, com zero linhas. Use o helper pelo
> motivo certo: ele corrige o comportamento, não um vazamento.

```python
op.execute("SET LOCAL lock_timeout = '3s'")

op.create_table(
    "nome_tabela",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
              server_default=sa.text("uuid_generate_v7()")),
    sa.Column("company_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    # ... colunas de domínio ...
    sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
              server_default=sa.text("now()")),
    sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
)

op.execute("ALTER TABLE nome_tabela ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE nome_tabela FORCE ROW LEVEL SECURITY")
op.execute(
    """
    CREATE POLICY nome_tabela_tenant_isolation ON nome_tabela
      USING (company_id = app_current_company_id())
      WITH CHECK (company_id = app_current_company_id())
    """
)
```

**Por que cada linha existe** — comportamento **medido** contra PostgreSQL, não deduzido
([ESPEC §7.6](ESPEC.md#76-o-que-foi-medido)):

| Linha | Se faltar | Modo |
|---|---|---|
| `ENABLE ROW LEVEL SECURITY` | Nenhuma proteção | 🔴 abre, em silêncio |
| `FORCE ROW LEVEL SECURITY` | O **dono** da tabela lê todos os tenants — medido | 🔴 abre, em silêncio |
| `WITH CHECK` | Numa policy `FOR ALL`, o Postgres usa o `USING` como check: escrita cross-tenant **continua** recusada. Mantenha mesmo assim — torna a intenção explícita e protege se alguém restringir a policy a `FOR SELECT` depois | 🟢 fecha |
| `app_current_company_id()` | Com contexto vazio, erro 500 em vez de negação limpa | 🟡 fecha, quebrado |
| `GRANT` (herdado da 0001) | `permission denied` | 🟢 fecha, barulhento |

Só duas peças falham abrindo, e as duas em silêncio — mais a view sem `security_invoker`
([ESPEC §7.4](ESPEC.md#74-views--a-falha-silenciosa-de-verdade)), que é a que mais vaza e a que a
checagem de tabelas não enxerga. É por isso que a verificação é consulta ao catálogo e os testes
incluem o **positivo**: as duas tabelas do experimento passariam em qualquer teste só-negativo,
inclusive a que vazava.

---

## 3. Enums

```sql
CREATE TYPE despesa_status            AS ENUM ('prevista','paga','cancelada');
CREATE TYPE medicao_status            AS ENUM ('rascunho','aprovada');
CREATE TYPE recebimento_status        AS ENUM ('previsto','recebido');
CREATE TYPE cronograma_periodicidade  AS ENUM ('semanal','mensal');
```

`despesa_status` não tem `atrasada`: atraso é **derivado** de `vencimento < hoje AND status =
'prevista'`. Persistir atraso exigiria job diário e produziria estado mentiroso entre as
execuções.

---

## 4. Tabelas

### 4.1 `obra_fase` — a identidade estável da fase

A tabela que resolve o problema do [ESPEC §4](ESPEC.md#4-fase-como-identidade-da-obra). É o eixo
de apropriação de todo o módulo.

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | Identidade **estável** da fase, sobrevive a revisão de orçamento |
| `company_id` | UUID FK | ✗ | Tenant |
| `obra_id` | UUID FK obras | ✗ | A obra. `NO ACTION` |
| `codigo` | TEXT | ✗ | Código da fase no orçamento. **É a chave de reconciliação entre versões** — mudar o código de uma fase com despesa lançada quebra o casamento |
| `descricao` | TEXT | ✗ | Nome da fase, atualizado a cada sincronização |
| `valor_orcado` | NUMERIC(18,2) | ✗ | Custo direto orçado da fase na versão aprovada. Desnormalizado **de propósito**: só muda na aprovação de versão, evento conhecido ([ESPEC §6.5](ESPEC.md#65-desempenho)) |
| `sort_order` | INTEGER | ✗ | Ordem de exibição, espelha a do orçamento |
| `ativa` | BOOLEAN | ✗ | `false` quando a fase sumiu da versão aprovada mais recente. **Nunca apagar** — pode ter despesa |
| `orcamento_versao_id` | UUID FK | ✓ | Versão que originou a última sincronização. Rastreabilidade, não dependência |
| `created_at` · `deleted_at` | TIMESTAMPTZ | | |

**Constraints**
```sql
UNIQUE (obra_id, codigo)                        -- a chave de reconciliação
CHECK  (valor_orcado >= 0)
```

**Índices**
```sql
(company_id, obra_id, sort_order)               -- listagem ordenada
```

**Leitura:** papéis de [ESPEC §9](ESPEC.md#9-autorização), via RLS.
**Escrita:** **apenas** o service de sincronização, disparado na aprovação de versão de
orçamento. Nenhuma rota de API escreve aqui — fase não se cria à mão, nasce do orçamento.

> **O que viola o propósito desta tabela:** criar fase diretamente, ou apagar fase inativa para
> "limpar". A segunda é destrutiva e silenciosa: a despesa fica com FK apontando para linha
> inexistente ou é removida em cascata.

---

### 4.2 `categoria_financeira` — plano de contas simples

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` | UUID FK | ✗ | Tenant. Categoria é da empresa, não da obra |
| `nome` | TEXT | ✗ | "Material", "Mão de obra", "Serviço de terceiro", "Equipamento", "Administrativo" |
| `ativa` | BOOLEAN | ✗ | Desativada some do formulário, **permanece** nos relatórios históricos (CA-F05.4) |
| `created_at` · `deleted_at` | TIMESTAMPTZ | | |

**Índice único** (não constraint — tem expressão **e** predicado, ver §1)
```sql
CREATE UNIQUE INDEX uq_categoria_company_nome ON categoria_financeira
  (company_id, lower(nome)) WHERE deleted_at IS NULL;
```
Sem o `lower`, "Material" e "material" coexistem; sem o predicado parcial, uma categoria
soft-deletada bloqueia a recriação do mesmo nome.

**Escrita:** `owner`, `admin`, `financeiro`.
**Seed:** o conjunto padrão é criado no primeiro acesso da empresa ao módulo, não por migration
— migration que insere dado por tenant não tem como saber quais tenants existirão.

---

### 4.3 `despesa` — contas a pagar

A tabela central do Módulo 6.

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` | UUID FK | ✗ | Tenant |
| `obra_id` | UUID FK obras | ✗ | A obra. `NO ACTION` |
| `obra_fase_id` | UUID FK obra_fase | ✗ | **A apropriação. NOT NULL é a RN-F02** — despesa sem fase torna o orçado × realizado impossível |
| `categoria_id` | UUID FK | ✗ | Natureza do gasto |
| `fornecedor_nome` | TEXT | ✗ | Nome digitado. Texto livre enquanto a US-03 não existir ([ESPEC §8](ESPEC.md#8-fornecedor-sem-cadastro)) |
| `fornecedor_id` | UUID | ✓ | **Sem FK por ora** — a tabela `fornecedores` não existe. Preparada para a reconciliação futura |
| `descricao` | TEXT | ✗ | O que foi comprado/contratado |
| `valor` | NUMERIC(18,2) | ✗ | Valor do título. `> 0` |
| `data_competencia` | DATE | ✗ | Quando o custo **aconteceu** — é o eixo do orçado × realizado |
| `vencimento` | DATE | ✗ | Quando vence — é o eixo do fluxo de caixa previsto |
| `status` | despesa_status | ✗ | `prevista` → comprometido · `paga` → realizado · `cancelada` → nenhum dos dois |
| `data_pagamento` | DATE | ✓ | Obrigatória sse `status='paga'`. É o eixo do fluxo de caixa realizado |
| `documento_id` | UUID FK documento | ✓ | NF anexada no GED. `ON DELETE SET NULL` — remover o vínculo não apaga o documento (CA-F07.3) |
| `grupo_parcelas_id` | UUID | ✓ | Agrupa parcelas da mesma compra. `NULL` = título avulso |
| `parcela_num` · `parcela_total` | SMALLINT | ✓ | `2` e `5` em "2/5". Nulos juntos quando não parcelado |
| `created_at` · `created_by` · `deleted_at` | | | |

**Constraints**
```sql
CHECK (valor > 0)
CHECK ((status = 'paga') = (data_pagamento IS NOT NULL))
CHECK ((parcela_num IS NULL) = (parcela_total IS NULL))
CHECK (parcela_num IS NULL OR (parcela_num >= 1 AND parcela_num <= parcela_total))
CHECK (grupo_parcelas_id IS NOT NULL OR parcela_num IS NULL)
```

O segundo `CHECK` é o que impede os dois estados mentirosos simétricos: título pago sem data, e
título com data de pagamento ainda marcado como previsto. Um `CHECK` só em uma direção deixa o
outro passar.

**Índices**
```sql
(company_id, obra_id, obra_fase_id, status) WHERE deleted_at IS NULL  -- agregação do realizado
(company_id, vencimento)                    WHERE deleted_at IS NULL  -- fluxo de caixa previsto
(company_id, id DESC)                       WHERE deleted_at IS NULL  -- paginação
(grupo_parcelas_id)                         WHERE grupo_parcelas_id IS NOT NULL
```

O primeiro é o que sustenta o RNF-F01: uma query com `GROUP BY obra_fase_id` e agregação
`FILTER (WHERE status = ...)`, não N+1 por fase.

**Escrita:** `owner`, `admin`, `financeiro` criam, editam e pagam. `gestor` cria e edita, **não**
paga. `campo`, `viewer`, `ai`: nenhum acesso.

> **Não existe coluna `atrasada`.** Atraso é `vencimento < CURRENT_DATE AND status = 'prevista'`.
> **Não existe `valor_pago`:** pagamento parcial está fora de escopo (PRD §3), e a coluna
> convidaria a implementá-lo pela metade.

---

### 4.4 `cronograma` — a linha de base

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` · `obra_id` | UUID FK | ✗ | |
| `orcamento_versao_id` | UUID FK | ✗ | A versão aprovada que originou a linha de base |
| `periodicidade` | cronograma_periodicidade | ✗ | `semanal` ou `mensal`, escolhida na criação e **imutável** |
| `data_inicio` | DATE | ✗ | Início do primeiro período |
| `bloqueado_em` | TIMESTAMPTZ | ✓ | Carimbado na primeira medição aprovada. Depois disso a distribuição não é editável (CA-F02.4) |
| `created_at` · `created_by` · `deleted_at` | | | |

**Índice único** (parcial — ver §1)
```sql
CREATE UNIQUE INDEX uq_cronograma_obra ON cronograma (obra_id) WHERE deleted_at IS NULL;
```
Um cronograma ativo por obra (CA-F01.5). Parcial: permite recriar depois de descartar o anterior.

> **Mudar a periodicidade depois de criado** invalidaria toda medição já vinculada a período.
> A alteração é feita descartando o cronograma e criando outro, e só é possível antes do
> bloqueio.

---

### 4.5 `cronograma_periodo`

| Coluna | Tipo | Nulo | Significado |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` | UUID FK | ✗ | Tenant — denormalizado para a RLS não precisar de join |
| `cronograma_id` | UUID FK | ✗ | `ON DELETE CASCADE` |
| `numero` | INTEGER | ✗ | Sequencial a partir de 1 |
| `inicio` · `fim` | DATE | ✗ | Limites do período, fechados nas duas pontas |

**Constraints**
```sql
UNIQUE (cronograma_id, numero)
CHECK  (fim >= inicio)
```

> `company_id` aqui é denormalização deliberada: sem ela, a policy de RLS precisaria de subquery
> na tabela pai, e policy que consulta outra tabela protegida é a receita da recursão descrita em
> [ESPEC §7](ESPEC.md#7-isolamento-multi-tenant). Vale para `cronograma_alocacao` e `medicao_item`
> pelo mesmo motivo.

---

### 4.6 `cronograma_alocacao` — fase × período

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` | UUID FK | ✗ | Denormalizado (ver 4.5) |
| `cronograma_id` · `periodo_id` · `obra_fase_id` | UUID FK | ✗ | A célula da grade |
| `percentual_planejado` | NUMERIC(7,4) | ✗ | Fração do **valor da fase** planejada neste período. `0 ≤ x ≤ 1` |
| `valor_planejado` | NUMERIC(18,2) | ✗ | `obra_fase.valor_orcado × percentual_planejado`, gravado para a Curva S não recalcular a cada leitura |

**Constraints**
```sql
UNIQUE (cronograma_id, periodo_id, obra_fase_id)
CHECK  (percentual_planejado >= 0 AND percentual_planejado <= 1)
```

**A regra que o banco não garante:** a soma de `percentual_planejado` de uma fase ao longo dos
períodos é exatamente 1 (RN-F07). `CHECK` não expressa agregação entre linhas. Quem garante é o
service, na gravação em bloco (`PUT /cronograma/{id}/alocacoes`), **com teste de borda em três
casas decimais** — somar 0,3333 três vezes dá 0,9999, e passar isso é o falso verde esperado
aqui.

---

### 4.7 `medicao`

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` · `obra_id` | UUID FK | ✗ | |
| `cronograma_id` · `periodo_id` | UUID FK | ✗ | O período medido |
| `status` | medicao_status | ✗ | `rascunho` → sem efeito · `aprovada` → **imutável**, gerou recebimento |
| `aprovada_em` | TIMESTAMPTZ | ✓ | Obrigatória sse `status='aprovada'` |
| `aprovada_por` | UUID FK users | ✓ | Idem. A trilha de aceite |
| `valor_liberado` | NUMERIC(18,2) | ✓ | Valor que virou título a receber. Gravado na aprovação, conforme RN-F06 |
| `observacao` | TEXT | ✓ | Justificativa, obrigatória por regra de serviço em medição de ajuste |
| `created_at` · `created_by` · `deleted_at` | | | |

**Constraints**
```sql
CHECK ((status = 'aprovada') = (aprovada_em IS NOT NULL))
CHECK (valor_liberado IS NULL OR valor_liberado > 0)
```

> **Por que o segundo `CHECK` não é `aprovada_em IS NULL OR valor_liberado IS NOT NULL`.** Era, e
> **contradizia o CA-F04.7**: numa obra sem `valor_contrato` a medição é aprovável e **não** gera
> título, logo `valor_liberado` fica nulo com `aprovada_em` preenchido — o que aquele `CHECK`
> proibia. Quem implementasse os dois documentos escolheria entre violar a constraint e gravar
> `0` — e gravar `0` é justamente o resultado que a RN-F06 descarta ("sumiria em silêncio no
> contas a receber"). A forma atual garante o que importa: **título só existe com valor
> positivo**. Em medição aprovada, `valor_liberado IS NULL` tem significado definido — aprovada
> sem faturar — e é distinguível de zero, que não é gravável.

**Índice único** (parcial — ver §1)
```sql
CREATE UNIQUE INDEX uq_medicao_periodo_aprovada ON medicao (periodo_id)
  WHERE status = 'aprovada' AND deleted_at IS NULL;
```

Permite vários rascunhos e **uma só** medição aprovada por período. É a única unicidade do módulo
que não começa por `company_id`, e isso é intencional: `periodo_id` já é único globalmente e
pertence a um só cronograma, logo a uma só obra e empresa. `periodo_id` é **NOT NULL** — se fosse
nulável, nulos seriam distintos entre si, duas medições aprovadas sem período coexistiriam sem
erro, e o critério "segunda medição aprovada no mesmo período é recusada" ficaria verde sem
proteger nada.

> **Imutabilidade não é garantida pelo banco.** Não há trigger bloqueando `UPDATE` de medição
> aprovada — é regra de serviço (CA-F04.4) e precisa de teste próprio. Se a imutabilidade virar
> requisito duro, a forma correta é trigger, no mesmo espírito do `REVOKE UPDATE, DELETE` de
> `audit_log`.

---

### 4.8 `medicao_item`

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` | UUID FK | ✗ | Denormalizado (ver 4.5) |
| `medicao_id` | UUID FK | ✗ | `ON DELETE CASCADE` |
| `obra_fase_id` | UUID FK | ✗ | A fase medida |
| `percentual_acumulado` | NUMERIC(7,4) | ✗ | **Acumulado desde o início da obra**, não o avanço do período (RN-F05). `0 ≤ x ≤ 1` |
| `valor_medido` | NUMERIC(18,2) | ✗ | Valor correspondente ao acumulado, para a Curva S |

**Constraints**
```sql
UNIQUE (medicao_id, obra_fase_id)
CHECK  (percentual_acumulado >= 0 AND percentual_acumulado <= 1)
```

**A regra que o banco não garante:** o acumulado não pode ser menor que o da última medição
aprovada da mesma fase (RN-F05). Depende de comparação entre linhas de medições diferentes —
responsabilidade do service, com teste que tenta retroceder e espera 422.

> **O erro clássico aqui é semântico, não técnico:** gravar o avanço do período em vez do
> acumulado. Os dois são `NUMERIC(7,4)` entre 0 e 1 e o banco aceita os dois igualmente; a
> Curva S fica errada sem nenhum erro. O nome da coluna carrega a intenção de propósito.

---

### 4.9 `recebimento` — contas a receber

| Coluna | Tipo | Nulo | Significado · o que viola |
|---|---|:--:|---|
| `id` | UUID PK | — | |
| `company_id` · `obra_id` | UUID FK | ✗ | |
| `medicao_id` | UUID FK | ✗ | **A origem.** Título não nasce à mão (RN-F06, CA-F10.3) |
| `valor` | NUMERIC(18,2) | ✗ | `> 0`. Medição que daria valor ≤ 0 não é aprovável (CA-F04.5) |
| `vencimento` | DATE | ✗ | **Informado no payload de aprovação da medição.** Não há coluna de prazo em `obras` nem em `clientes`, então não há de onde derivar; o default sugerido na UI é +30 dias da aprovação, e o usuário ajusta |
| `status` | recebimento_status | ✗ | `previsto` ou `recebido` |
| `data_recebimento` | DATE | ✓ | Obrigatória sse `status='recebido'` |
| `created_at` · `deleted_at` | | | |

**Constraints**
```sql
CHECK (valor > 0)
CHECK ((status = 'recebido') = (data_recebimento IS NOT NULL))
```

**Índice único** (parcial — ver §1)
```sql
CREATE UNIQUE INDEX uq_recebimento_medicao ON recebimento (medicao_id)
  WHERE deleted_at IS NULL;   -- uma medição, um título
```

**Escrita:** o service de faturamento cria, na aprovação da medição. A API só expõe a transição
de status — não há `POST` de recebimento avulso.

---

## 5. Ordem de criação

Uma migration por sprint, forward-only. A ordem respeita as FKs: criar `despesa` antes de
`obra_fase` falha porque a FK não encontra o alvo.

| # | Migration | Cria | Sprint |
|---|---|---|---|
| 0032 | `obra_fase` | `obra_fase` | **S-F1** |
| 0033 | `financeiro_base` | enum `despesa_status`, `categoria_financeira`, `despesa` | **S-F3** |
| 0034 | `cronograma` | enum `cronograma_periodicidade`, `cronograma`, `cronograma_periodo`, `cronograma_alocacao` | **S-F5** |
| 0035 | `medicao` | enums `medicao_status` e `recebimento_status`, `medicao`, `medicao_item`, `recebimento` | **S-F7** |

> A S-F2 (contrato) e as sprints de frontend **não criam migration**. A primeira redação desta
> tabela apontava 0033→S-F2, 0034→S-F3 e 0035→S-F4, o que mandava uma sprint de frontend criar
> migration e colidia com os slots do [SPRINTS](SPRINTS.md). Em caso de divergência entre os dois
> documentos sobre *quando*, o SPRINTS manda; este dicionário manda sobre *o quê*.

> **O número 0032 pressupõe que nada mais tenha sido mergeado.** A última aplicada no `main` em
> `89593a5` é a `0031`. Confira antes de criar — colisão de número é conflito de merge, não erro
> de runtime, e aparece tarde.

---

## 6. Verificação do schema

Roda no mesmo comando dos testes, **consultando o catálogo** — busca textual no SQL não enxerga
tabela criada dentro de bloco anônimo nem RLS habilitada e desabilitada depois:

```sql
-- 1. RLS habilitada e forçada em todas as tabelas do módulo
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND c.relname IN ('obra_fase','categoria_financeira','despesa','cronograma',
                    'cronograma_periodo','cronograma_alocacao','medicao',
                    'medicao_item','recebimento')
  AND NOT (c.relrowsecurity AND c.relforcerowsecurity);
-- zero linhas = ok

-- 2. Policy com USING e WITH CHECK
SELECT c.relname, p.polname, p.polqual IS NOT NULL AS tem_using,
       p.polwithcheck IS NOT NULL AS tem_with_check
FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid
WHERE c.relname IN (...) AND (p.polqual IS NULL OR p.polwithcheck IS NULL);
-- zero linhas = ok

-- 3. GRANT para app_user
SELECT c.relname
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname IN (...)
  AND NOT has_table_privilege('app_user', c.oid, 'SELECT, INSERT, UPDATE, DELETE');
-- zero linhas = ok

-- 4. Nenhuma view sem security_invoker sobre tabela do módulo
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'v'
  AND COALESCE((SELECT option_value FROM pg_options_to_table(c.reloptions)
                WHERE option_name = 'security_invoker'), 'false') <> 'true';
-- zero linhas = ok (o módulo não cria views — ESPEC §7.4)
```

Estes quatro **não substituem** os testes de isolamento. Verificam que o mecanismo está montado;
os testes verificam que ele funciona — incluindo o **positivo** (tenant A vê as próprias linhas),
sem o qual um schema com RLS e zero policies passa em tudo.

E há um limite importante: **as quatro consultas rodam como superusuário e não detectam
`FORCE ROW LEVEL SECURITY` ausente em runtime** — a Q1 confere a flag no catálogo, mas a fixture
de teste do projeto conecta como `app_user`, que não é dono da tabela e por isso nunca exercita
o caminho que vaza. A Q1 é a única verificação dessa peça; se ela não rodar, ninguém pega.

**Onde isto roda.** `make test` é `uv run pytest` com `testpaths = ["tests"]` — um script em
`backend/scripts/` **não é coletado**. O verificador precisa ser invocado por um teste em
`backend/tests/`, como já faz `tests/test_documento_check_db.py`. 

**"Nenhum `float` em cálculo financeiro" não entra aqui:** não se detecta tipo de Python
consultando `pg_catalog`. É verificação de código — `grep` no diff ou regra de lint —, não de
schema.

### 6.1 Constraints de `medicao` — medidas, não deduzidas

As constraints da §4.7 foram aplicadas num Postgres 16 e exercitadas com `INSERT`, em
2026-11-02. O resultado de cada caso:

| Caso | Esperado | Medido |
|---|---|---|
| Aprovada com `valor_liberado` nulo (CA-F04.7) | aceita | **aceita** |
| Aprovada com `valor_liberado = 0` | recusa | **recusa** — `medicao_valor_liberado_check` |
| `rascunho` com `aprovada_em` preenchido | recusa | **recusa** — `medicao_check` |
| Segunda aprovada no mesmo `periodo_id` | recusa | **recusa** — `uq_medicao_periodo_aprovada` |
| Vários rascunhos no mesmo `periodo_id` | aceita | **aceita** (2 linhas) |

A primeira linha é a que justifica a mudança: com o `CHECK` anterior ela era **recusada**, e o
CA-F04.7 era impossível de implementar sem violar o schema. Nenhuma releitura tinha pegado isso.

---

## 7. O que este dicionário deliberadamente não tem

| Ausência | Por quê |
|---|---|
| `despesa.valor_pago` | Pagamento parcial fora de escopo. A coluna convidaria a meia implementação |
| `despesa.atrasada` | Derivado de `vencimento` e `status`. Persistir exigiria job e mentiria entre execuções |
| Tabela de tributos ou retenções | Controle gerencial, não apuração fiscal (PRD §3) |
| `nfe_chave`, `nfe_xml` | NF-e é Fase 3 |
| Tabela de conciliação bancária | Fora de escopo |
| `moeda` | BRL implícita |
| Views de agregação | Risco de `security_invoker` esquecido; as agregações são queries no service |
| Coluna de centro de custo | O eixo de análise é a obra e a fase |

---

*Dicionário Módulos 5 e 6, versão 1.0. As convenções foram extraídas das migrations 0001 a 0031
do repositório; a advertência de §2 sobre o template antigo vem da comparação entre a migration
0023 e a 0030.*
