# SPRINTS — Módulos 5 e 6

**Versão:** 1.0 | **Data:** 2026-11-02
**Consome:** [PRD](PRD.md) · [ESPEC](ESPEC.md) · [Dicionário](DICIONARIO-DE-DADOS.md)
**Executor:** agentes, uma sprint por sessão

> ⚠️ **`docs/PROMPT-ORQUESTRADOR.md` não existe no repositório.** Foi escrito em 2026-08-28 e
> nunca mergeado — o mesmo vale para `docs/REFATORACAO.md`. Enquanto não existirem, cada sprint
> é despachada com as [Regras de execução](#regras-de-execução) abaixo coladas junto. Documento
> referenciado e ausente trava o orquestrador antes de começar, então a referência fica aqui
> como pendência explícita, não como link.
**Base:** `main` em `89593a5` · última migration aplicada `0031`

---

## Regras de execução

1. **Só edite os arquivos listados em `Arquivos`.** Precisando de algo fora, **reporte em vez de
   editar** — arquivo fora da lista pertence a outra sprint e editá-lo produz conflito de merge.
2. **Definição de concluído:** `make test && make lint` verdes, mais os gates de frontend
   (`pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build:budget`, `pnpm test:e2e`) quando a sprint
   os toca. Sem exceção.
   **`make check-contract` não existe** — foi escrito em 2026-08-28 e nunca mergeado, e o
   `Makefile` não está na lista de arquivos de nenhuma sprint. Criá-lo é trabalho de outra
   frente; não bloqueie uma sprint por ele.
3. **Teto de 3 ciclos de correção** por sprint. Estourou, a sprint é bloqueada e volta para
   replanejamento — não para um quarto ciclo.
4. **Sprint com `Revisor de segurança: sim` não fecha sem essa revisão**, além dos gates. O
   revisor é o agente **`revisor-isolamento`** (`.claude/agents/`), que precisa ter **rodado** as
   consultas de catálogo do [Dicionário §6](DICIONARIO-DE-DADOS.md#6-verificação-do-schema) — não
   lido o diff. Revisor genérico não serve aqui: os dois vazamentos silenciosos deste schema
   (`FORCE ROW LEVEL SECURITY` ausente e view sem `security_invoker`) não aparecem em leitura.
   Este campo **não** é o caminho crítico: são coisas diferentes e estavam com o mesmo nome. A
   S-F2 está no caminho crítico e não pede revisor; a S-F3 pede revisor e não está no caminho
   crítico. Confundir os dois leva a priorizar a trilha errada.
5. **Slot de migration é data.** Duas sprints paralelas gerando migration no mesmo instante
   produzem ordem não determinística entre branches.
6. Ao mudar contrato de API, atualize o schema Pydantic, o teste **e o handler MSW** na mesma
   sprint — senão o mock passa a mentir, que é como uma rota inexistente chega à `main` com todos
   os gates verdes.
7. **Despacho:** `.claude/commands/orquestrador-financeiro.md`, que também traz a baseline medida
   da `main` (17 testes vermelhos conhecidos, todos de mock S3 — não são regressão). Divergências
   abertas com o resto do projeto: [ERRATA.md](ERRATA.md) — a **E-01** bloqueia a Onda 3 até haver
   decisão humana.

---

## Ondas e caminho crítico

```
Onda 0   S-F1  fundação: fase como identidade          (bloqueia tudo)
           │
Onda 1   S-F2  contrato da API                         (destrava 2 e 3 em paralelo)
           ├──────────────────────────┐
Onda 2   backend                      Onda 3   frontend (contra MSW)
  S-F3 despesas  ‖  S-F5 cronograma     S-F4 despesas  ‖  S-F6 cronograma
            S-F7 medição ◄── S-F5       S-F8 medição
            S-F9 análise ◄── F3+F7      S-F10 análise
           └──────────────────────────┘
Onda 4   S-F11 hardening + habilitar a sidebar
```

**Caminho crítico:** `S-F1 → S-F2 → S-F5 → S-F7 → S-F9 → S-F11`.
Medição depende de período do cronograma, e a análise depende de despesa e medição. Despesas
(S-F3) corre em paralelo ao cronograma e **não** está no caminho crítico — proteger a trilha de
despesas achando que ela é o gargalo é o erro de alocação mais provável aqui.

**O que destrava o paralelismo das ondas 2 e 3:** a S-F2 entrega os schemas Pydantic completos e
as rotas registradas devolvendo 501, **com o schema de resposta de sucesso declarado**. Stub que
só devolve o código de erro faz o frontend construir contra `unknown` e passar no critério "o
contrato gera sem erro" sem tipo nenhum.

---

## Onda 0

### Sprint S-F1 — Fundação: fase como identidade da obra

- **Agente:** postgres-dba
- **Depende de:** —
- **Paralela com:** —
- **Revisor de segurança:** sim
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** 2026-11-03 · `0032`
- **Arquivos:**
  `backend/alembic/versions/0032_obra_fase.py` ·
  `backend/app/modules/financeiro/__init__.py` ·
  `backend/app/modules/financeiro/services/fases.py` ·
  `backend/app/modules/orcamento/services/orcamentos.py` *(hook de sincronização na aprovação)* ·
  **`backend/app/modules/portal/service.py`** *(o **segundo** ponto de aprovação — o cliente
  aprovando pelo portal; sem o hook aqui o módulo inteiro nasce morto, ver
  [ESPEC §4.1](ESPEC.md#41-onde-a-sincronização-é-disparada))* ·
  `backend/app/modules/financeiro/services/__init__.py` ·
  `backend/tests/test_obra_fase.py` ·
  `backend/tests/test_rls_financeiro.py` ·
  `backend/scripts/check_schema_financeiro.py`
- **Escopo:** tabela `obra_fase` conforme [Dicionário §4.1](DICIONARIO-DE-DADOS.md), com RLS pelo
  template de [§2](DICIONARIO-DE-DADOS.md); service de sincronização disparado na aprovação de
  versão de orçamento; script de verificação de schema de [§6](DICIONARIO-DE-DADOS.md).
- **Fora de escopo:** qualquer rota de API; qualquer tela; as outras oito tabelas.
- **Critérios de aceite:**
  - [ ] Aprovar uma versão de orçamento cria uma `obra_fase` por item `tipo='F'`, com
        `valor_orcado` igual ao custo direto agregado da fase — **positivo**, conferido contra
        valores calculados à mão na fixture
  - [ ] Aprovar uma **segunda** versão com o mesmo código de fase atualiza descrição e valor, e
        **mantém o mesmo `id`** — é a reconciliação da RN-F03
  - [ ] Código de fase que sumiu da nova versão fica `ativa = false`, não é apagado
  - [ ] Código novo na segunda versão cria fase nova
  - [ ] `UNIQUE (obra_id, codigo)` rejeita duplicata
  - [ ] Tenant A **vê as próprias** `obra_fase` (positivo de isolamento, SEC-F03)
  - [ ] Tenant A recebe zero linhas das fases de B, em leitura **e** escrita (SEC-F02)
  - [ ] `check_schema_financeiro.py` confere RLS, policy com `USING` e `WITH CHECK`, e `GRANT`
        pelo catálogo, e falha se qualquer um faltar
  - [ ] A policy usa `app_current_company_id()`, não o cast cru — grep na migration confirma
  - [ ] **Aprovar pela rota `PATCH /orcamentos/{id}/status` cria as fases** — o teste chama a
        rota, não o service
  - [ ] **Aprovar pelo portal cria as fases** — idem, pela rota de decisão do portal. Os dois
        caminhos, senão o módulo nasce morto no fluxo real ([ESPEC §4.1](ESPEC.md#41-onde-a-sincronização-é-disparada))
  - [ ] Fase sem `codigo` recebe o código sintético `F{sort_order:03d}` e o INSERT passa
  - [ ] Duas fases com o mesmo código na mesma versão **recusam a aprovação** com 422 nomeando
        as fases — não deduplica em silêncio

> O critério da segunda versão é o que importa mais nesta sprint, e é o único que exercita o
> caminho que só aconteceria em produção no dia da primeira revisão de orçamento. A fixture monta
> duas versões mesmo que a US-16 não exista.

---

## Onda 1

### Sprint S-F2 — Contrato da API

- **Agente:** backend-developer
- **Depende de:** S-F1
- **Paralela com:** —
- **Revisor de segurança:** não
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** — (não cria migration)
- **Arquivos:**
  `backend/app/modules/financeiro/schemas/*.py` ·
  `backend/app/modules/financeiro/routers/*.py` ·
  **`backend/app/api/v1/__init__.py`** *(registro dos routers — este arquivo é desta sprint e de
  mais nenhuma; as sprints seguintes não o tocam)* ·
  `backend/tests/test_financeiro_contrato.py` ·
  `frontend/lib/api/types.ts` ·
  `frontend/lib/api/financeiro.ts` ·
  `frontend/lib/mock/handlers.ts` · `frontend/lib/mock/db.ts`
- **Escopo:** todos os schemas Pydantic de [ESPEC §6](ESPEC.md#6-contratos-de-api); todas as rotas
  registradas devolvendo **501** com `response_model` declarado; tipos TS e client do frontend;
  handlers MSW devolvendo dados de exemplo coerentes com os schemas.
- **Fora de escopo:** qualquer regra de negócio; qualquer persistência; qualquer tela.
- **Critérios de aceite:**
  - [ ] **(positivo)** As **25 operações** de [ESPEC §6](ESPEC.md#6-contratos-de-api) aparecem no
        OpenAPI, e as **24** que devolvem JSON trazem o `response_model` de sucesso — o schema de
        resposta está lá, não só o 501. A 25ª é `export.csv`, que devolve `text/csv` e não tem
        modelo Pydantic
  - [ ] `make check-contract` verde: toda rota chamada por `frontend/lib/api/financeiro.ts`
        existe no OpenAPI
  - [ ] Todo schema tem `extra='forbid'`; campo desconhecido devolve 422
  - [ ] Valores monetários são `Decimal` nos schemas, nunca `float`
  - [ ] Percentuais são `Decimal` e documentados como fração no docstring do schema
  - [ ] Os handlers MSW devolvem payload que **valida contra os schemas** — teste que carrega o
        exemplo do mock e valida com o Pydantic
  - [ ] `pnpm exec tsc --noEmit` verde: o frontend compila contra os tipos novos
  - [ ] **Nenhum `response_model` do módulo é `dict`, `Any` ou `JSONResponse`** — cada campo do
        schema de resposta aparece nomeado no OpenAPI. Sem isto, o stub compila e o frontend
        constrói contra `unknown`, passando no critério sem contrato nenhum
  - [ ] A contagem no OpenAPI bate com a de [ESPEC §6](ESPEC.md#6-contratos-de-api). Os três
        números são diferentes e é fácil conferir contra o errado — **contados linha a linha:
        21 linhas de rota, 19 paths distintos, 25 operações**. Três linhas valem mais de uma
        operação (`GET,POST /financeiro/categorias`, `GET,POST /obras/{obra_id}/despesas`,
        `GET,PATCH,DELETE /financeiro/despesas/{id}`), e dois paths aparecem em duas linhas. O
        número que o OpenAPI expõe é **25**

> O último critério é o que impede o mock de divergir do backend desde o primeiro dia. Sem ele, o
> frontend constrói contra um contrato que ninguém conferiu.

---

## Onda 2 — backend

### Sprint S-F3 — Despesas

- **Agente:** backend-developer · tasks `DB-*` para postgres-dba
- **Depende de:** S-F2
- **Paralela com:** S-F5, S-F4, S-F6
- **Revisor de segurança:** sim (escrita financeira + isolamento)
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** 2026-11-05 · `0033`
- **Arquivos:**
  `backend/alembic/versions/0033_financeiro_base.py` ·
  `backend/app/modules/financeiro/routers/despesas.py` · `routers/categorias.py` ·
  `backend/app/modules/financeiro/services/despesas.py` ·
  `backend/tests/test_despesas.py` · `test_categorias.py` · `test_despesa_parcelamento.py` ·
  `backend/tests/test_rls_financeiro.py` *(acrescenta as tabelas novas; arquivo criado na S-F1)* ·
  `backend/scripts/check_schema_financeiro.py` *(acrescenta as tabelas novas)*
- **Escopo:** `categoria_financeira` e `despesa` conforme Dicionário §4.2 e §4.3; CRUD; seed das
  categorias padrão no primeiro acesso; parcelamento; pagar e estornar.
- **Fora de escopo:** anexo de NF *(S-F11)*; telas; agregações de análise.
- **Tasks:** `DB-01` migration · `DB-02` índices · `DB-03` RLS e policies · `BE-01` repository ·
  `BE-02` service de parcelamento (RN-F08) · `BE-03` rotas · `QA-01` isolamento
- **Critérios de aceite:**
  - [ ] Despesa criada com fase, categoria, valor e datas **aparece na listagem da obra**
        (positivo)
  - [ ] Despesa sem `obra_fase_id` é recusada com 422 (RN-F02)
  - [ ] Valor zero ou negativo é recusado
  - [ ] Parcelar 1000,00 em 3 gera 333,33 + 333,33 + 333,34, **somando exatamente 1000,00**
  - [ ] Parcelas herdam obra, fase, categoria e fornecedor, e têm vencimentos mensais
  - [ ] Pagar exige data e muda o status; o `CHECK` rejeita pago sem data **e** data sem pago
  - [ ] Estornar devolve a despesa para `prevista` e limpa a data
  - [ ] Categoria com despesa vinculada não é excluível, só desativável
  - [ ] Categoria desativada some do formulário e **continua** nos relatórios
  - [ ] Despesa em obra de outro tenant: 404, não 403 (SEC-F04)
  - [ ] Papel `campo` e `viewer` recebem 403 em todas as rotas (SEC-F05)
  - [ ] Pagamento e exclusão geram `audit_log` (SEC-F07)
  - [ ] **Despesa paga sai do comprometido e entra no realizado da fase** — sem este, `pagar`
        pode ser um `UPDATE` de status sem efeito semântico nenhum e passa em tudo
  - [ ] O `audit_log` do pagamento é **distinguível** de um `PATCH` de descrição: o teste
        confere o campo alterado, não só a existência de linha. O trigger genérico grava
        `action='UPDATE'` para qualquer coisa, inclusive para o soft delete
  - [ ] Papel `ai` também recebe 403 — não só `campo` e `viewer`
  - [ ] Nenhum `float` no caminho de cálculo — verificação por `grep`/`ruff` no diff, não por
        catálogo do Postgres (catálogo não enxerga tipo de Python)
  - [ ] **O seed das categorias padrão roda uma vez por empresa e é idempotente sob concorrência.**
        O CA-F05.1 diz "criado no primeiro acesso" e não diz quem dispara nem o que acontece em
        dois acessos simultâneos: duas requisições que não acham categoria nenhuma inserem o
        conjunto as duas, e a segunda bate em `uq_categoria_company_nome` — o primeiro acesso da
        empresa falha com 500. Resolva **no banco** (`INSERT ... ON CONFLICT DO NOTHING`), não com
        trava em memória: uma instância não é um processo. Teste com duas sessões concorrentes, e
        confira que o resultado tem o conjunto **uma** vez

### Sprint S-F5 — Cronograma

- **Agente:** backend-developer
- **Depende de:** S-F2
- **Paralela com:** S-F3, S-F4, S-F6
- **Revisor de segurança:** não
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** 2026-11-06 · `0034`
- **Arquivos:**
  `backend/alembic/versions/0034_cronograma.py` ·
  `backend/app/modules/financeiro/routers/cronograma.py` ·
  `backend/app/modules/financeiro/services/cronograma.py` ·
  `backend/tests/test_cronograma.py` ·
  `backend/tests/test_rls_financeiro.py` · `backend/scripts/check_schema_financeiro.py`
- **Escopo:** `cronograma`, `cronograma_periodo`, `cronograma_alocacao` conforme Dicionário §4.4
  a §4.6; geração dos períodos; distribuição linear inicial; ajuste em bloco; bloqueio após a
  primeira medição aprovada.
- **Fora de escopo:** medição *(S-F7)*; Curva S *(S-F9)*; telas.
- **Critérios de aceite:**
  - [ ] Criar cronograma de obra com versão aprovada gera períodos cobrindo `data_inicio` até
        `data_prevista_fim`, na periodicidade escolhida (positivo)
  - [ ] A distribuição inicial é linear e **cada fase soma exatamente 1,0000**
  - [ ] O total planejado é igual ao `custo_direto` da versão aprovada
  - [ ] Obra sem orçamento aprovado recusa a criação, com mensagem dizendo o que falta
  - [ ] Segundo cronograma na mesma obra é recusado pelo índice único parcial
  - [ ] Ajuste cuja fase soma 0,9999 é **recusado**, e a mensagem nomeia a fase e a diferença —
        é o caso de borda de três casas decimais, o falso verde esperado aqui
  - [ ] Ajuste válido grava e recalcula `valor_planejado` de cada célula
  - [ ] Periodicidade não é alterável depois de criada
  - [ ] **A soma de `valor_planejado` de cada fase é exatamente `obra_fase.valor_orcado`** — o
        critério de percentual fecha em 1,0000 e ainda assim os valores podem dar 999,99
  - [ ] Obra sem `data_inicio` ou sem `data_prevista_fim` devolve **422** nomeando a data que
        falta, não 500 ([ESPEC §4.4](ESPEC.md#44-os-casos-de-borda-que-o-schema-permite))
  - [ ] Isolamento nas três tabelas, positivo e negativo

### Sprint S-F7 — Medição e faturamento

- **Agente:** backend-developer
- **Depende de:** S-F5
- **Paralela com:** S-F4, S-F6, S-F8
- **Revisor de segurança:** sim (gera título financeiro e é a trilha de aceite com o cliente)
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** 2026-11-10 · `0035`
- **Arquivos:**
  `backend/alembic/versions/0035_medicao.py` ·
  `backend/app/modules/financeiro/routers/medicao.py` · `routers/recebimentos.py` ·
  `backend/app/modules/financeiro/services/medicao.py` · `services/faturamento.py` ·
  `backend/app/modules/financeiro/services/cronograma.py` *(carimbar `bloqueado_em`)* ·
  `backend/tests/test_medicao.py` · `test_faturamento.py` ·
  `backend/tests/test_rls_financeiro.py` · `backend/scripts/check_schema_financeiro.py`
- **Escopo:** `medicao`, `medicao_item`, `recebimento` conforme Dicionário §4.7 a §4.9; rascunho,
  gravação em bloco, aprovação; cálculo do valor liberado (RN-F06); geração do título a receber;
  transição de recebido.
- **Fora de escopo:** telas; régua de cobrança; Curva S.
- **Critérios de aceite:**
  - [ ] Medição aprovada **gera um título a receber** com o valor da RN-F06 **ponderada**,
        conferido contra cálculo à mão (positivo)
  - [ ] **Obra com 5 fases de peso igual, todas a 20%, libera 20% do contrato — não 100%.**
        É o critério que separa a fórmula ponderada da ingênua; a ingênua multiplica o contrato
        pelo número de fases
  - [ ] Obra sem `valor_contrato` aprova a medição **sem** gerar título, e avisa (CA-F04.7). No
        banco: `aprovada_em` preenchido, `valor_liberado` **nulo**, zero linhas em `recebimento`.
        **Nulo e zero não são a mesma coisa aqui** — gravar `0` passa numa leitura distraída do
        critério e é o estado que a RN-F06 recusa, porque um título de zero desaparece em
        silêncio no contas a receber
  - [ ] `medicao_item.valor_medido` usa a **mesma base** de `cronograma_alocacao.valor_planejado`
        (`obra_fase.valor_orcado × percentual`), senão a Curva S não fecha com o orçado ×
        realizado
  - [ ] Percentual acumulado menor que o da medição aprovada anterior é recusado com 422 (RN-F05)
  - [ ] Percentual acima de 1,0000 é recusado
  - [ ] Segunda medição aprovada no mesmo período é recusada pelo índice único parcial
  - [ ] Medição aprovada não aceita `PUT` nos itens: 409 com o caminho da medição de ajuste
  - [ ] **Numa obra com `valor_contrato`**, medição cujo valor liberado daria ≤ 0 não é aprovável
        (CA-F04.5). Sem a ressalva este critério e o anterior se contradizem, e o agente escolhe
        um dos dois
  - [ ] A primeira aprovação carimba `cronograma.bloqueado_em`, e a partir daí o ajuste de
        alocação é recusado
  - [ ] Só `owner` e `admin` aprovam; `financeiro` e `gestor` recebem 403 (ESPEC §9)
  - [ ] Não existe `POST` de recebimento avulso — a rota não está no OpenAPI
  - [ ] Aprovação gera `audit_log` com autor e horário
  - [ ] Isolamento nas três tabelas, positivo e negativo

### Sprint S-F9 — Análise: orçado × realizado, Curva S, fluxo de caixa

- **Agente:** backend-developer
- **Depende de:** S-F3, S-F7
- **Paralela com:** S-F8, S-F10
- **Revisor de segurança:** não
- **Status:** pendente
- **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** — (sem migration; só índices já criados)
- **Arquivos:**
  `backend/app/modules/financeiro/routers/analise.py` ·
  `backend/app/modules/financeiro/services/orcado.py` · `services/curva_s.py` ·
  `services/fluxo_caixa.py` ·
  `backend/tests/test_orcado_realizado.py` · `test_curva_s.py` · `test_fluxo_caixa.py` ·
  `backend/tests/test_financeiro_performance.py`
- **Escopo:** as três agregações de [ESPEC §6.3](ESPEC.md#63-análise); cálculo de comprometido
  separado do realizado (RN-F04); alerta de estouro na leitura.
- **Fora de escopo:** exportação *(S-F11)*; telas; cache.
- **Critérios de aceite:**
  - [ ] Obra com despesas em três fases mostra **cada uma na fase certa**, com valores conferidos
        à mão (positivo — sem ele a tela passa estando vazia, CA-F11.5)
  - [ ] Realizado conta só `paga`; comprometido conta só `prevista`; `cancelada` não entra em
        nenhum dos dois
  - [ ] Fase com realizado + comprometido acima do orçado vem marcada com `estourada = true`
  - [ ] Fase dentro do orçado vem com `estourada = false` — o par positivo, sem o qual "não
        dispara quando está dentro" ficaria verde com alerta que nunca dispara
  - [ ] Os totais da obra batem com a soma das fases
  - [ ] Obra sem orçamento aprovado devolve estado vazio sinalizado, **não zeros** (CA-F11.4)
  - [ ] Curva S devolve as três séries acumuladas por período, e os valores conferem com os da
        tela de orçado × realizado (CA-F12.5)
  - [ ] Período sem movimento aparece com zero no fluxo de caixa, não some da série
  - [ ] Orçado × realizado com 50 fases e 2000 despesas em < 1s (RNF-F01), medido em teste
  - [ ] Curva S com 24 períodos e 50 fases em < 300ms (RNF-F02)
  - [ ] **Fase sem nenhuma despesa aparece na lista com realizado 0 e comprometido 0** — o
        filtro de `deleted_at` vai na condição do `JOIN`, não no `WHERE`, senão as fases ainda
        não gastas somem e Carlos perde justamente as que importam
  - [ ] O eixo de data está declarado e testado: orçado × realizado por `data_competencia`,
        fluxo de caixa realizado por `data_pagamento`, Curva S financeira por `data_pagamento`.
        Despesa fora da janela do cronograma entra no primeiro ou no último período, nunca some
  - [ ] A agregação é **uma** query com `GROUP BY`, não N+1 — teste que conta queries, mais
        `EXPLAIN` confirmando index scan (há precedente em `tests/test_indices_paginacao.py`)

---

## Onda 3 — frontend

> As quatro sprints desta onda constroem contra o MSW entregue na S-F2 e rodam em paralelo com a
> onda 2. Nenhuma delas toca `frontend/components/shared/Sidebar.tsx` — habilitar o item é da
> S-F11, porque item habilitado apontando para tela incompleta é pior que item desabilitado.

### Sprint S-F4 — Telas de despesa

- **Agente:** nextjs-developer
- **Depende de:** S-F2
- **Paralela com:** S-F3, S-F5, S-F6
- **Revisor de segurança:** não
- **Status:** pendente · **Ciclos:** 0/3 · **Revisores OK:** —
- **Arquivos:**
  `frontend/app/(admin)/obras/[id]/financeiro/despesas/page.tsx` ·
  `frontend/components/modules/financeiro/DespesasTable.tsx` ·
  `DespesaFormDrawer.tsx` · `ParcelamentoFields.tsx` · `PagamentoDialog.tsx` ·
  **`frontend/components/shared/MoneyInput.tsx`** *(não existe no projeto — esta sprint o cria)* ·
  `frontend/lib/hooks/use-despesas.ts` · `use-categorias.ts` ·
  `frontend/app/(admin)/configuracoes/categorias/page.tsx` ·
  `frontend/components/modules/financeiro/CategoriasList.tsx` ·
  `frontend/e2e/financeiro-despesas.spec.ts`
- **Escopo:** US-F05, US-F06, US-F08, US-F09 na interface.
- **Fora de escopo:** anexo de NF *(S-F11)*; sidebar.
- **Critérios de aceite:**
  - [ ] Lançar despesa com fase, categoria, fornecedor, valor e datas **a faz aparecer na lista**
        (positivo, E2E)
  - [ ] O seletor de fase lista as fases da obra, e submeter sem fase é barrado no client
  - [ ] `MoneyInput` criado: digita em centavos, exibe pt-BR, devolve decimal canônico
  - [ ] Nenhum `toFixed()` sobre `Number` (RN-F10). **Atenção:** `lib/format.ts` faz
        `Number(value)` internamente — use `lib/decimal.ts`. E `formatPercent` dos dois módulos
        tem semântica oposta: o de `format.ts` multiplica por 100, o de `decimal.ts` não. Os
        percentuais deste módulo são frações
  - [ ] Parcelamento mostra as parcelas geradas antes de confirmar
  - [ ] Pagar pede data e atualiza a linha sem recarregar a página
  - [ ] Loading com skeleton, empty com CTA, error com retry
  - [ ] axe-core sem violação crítica (RNF-F05). **As rotas novas entram no array `ADMIN_PAGES`
        de `frontend/e2e/a11y.spec.ts`, que é editado só na S-F11** — até lá, rode o axe dentro
        do spec da própria sprint reaproveitando a allowlist de contraste das cores de marca, ou
        reporte. Escrever um `AxeBuilder` novo reprova nas violações de `#ff6b6b`/`#845ef7` que o
        projeto já decidiu tolerar
  - [ ] Bundle da rota dentro do teto de 240 kB

### Sprint S-F6 — Tela de cronograma

- **Agente:** nextjs-developer
- **Depende de:** S-F2 · **Paralela com:** S-F3, S-F4, S-F5
- **Revisor de segurança:** não · **Status:** pendente · **Ciclos:** 0/3 · **Revisores OK:** —
- **Arquivos:**
  `frontend/app/(admin)/obras/[id]/cronograma/page.tsx` ·
  `frontend/components/modules/financeiro/CronogramaGrid.tsx` · `CronogramaToolbar.tsx` ·
  `frontend/lib/hooks/use-cronograma.ts` ·
  `frontend/e2e/financeiro-cronograma.spec.ts`
- **Escopo:** US-F01 e US-F02.
- **Fora de escopo:** gerar o cronograma *(backend, S-F5)*; medição *(S-F8)*; Curva S *(S-F10)*;
  sidebar *(S-F11)*. Esta sprint **não** adiciona biblioteca de grade nem de drag-and-drop: a grade
  é tabela com `input` por célula.
- **Critérios de aceite:**
  - [ ] A grade mostra fases nas linhas e períodos nas colunas, com totais de linha e coluna
  - [ ] Editar uma célula recalcula os totais na hora (positivo)
  - [ ] Fase que não soma 100% aparece destacada **com texto**, não só cor, e o botão de salvar
        fica desabilitado com o motivo visível
  - [ ] Cronograma bloqueado abre em leitura, com aviso explicando por quê
  - [ ] Obra sem orçamento aprovado mostra empty com CTA
  - [ ] axe-core sem violação crítica; a grade é navegável por teclado

### Sprint S-F8 — Telas de medição

- **Agente:** nextjs-developer
- **Depende de:** S-F2 · **Paralela com:** S-F7, S-F9, S-F10
- **Revisor de segurança:** não · **Status:** pendente · **Ciclos:** 0/3 · **Revisores OK:** —
- **Arquivos:**
  `frontend/app/(admin)/obras/[id]/medicoes/page.tsx` ·
  `frontend/app/(admin)/obras/[id]/medicoes/[medicaoId]/page.tsx` ·
  `frontend/components/modules/financeiro/MedicaoForm.tsx` · `MedicaoList.tsx` ·
  `AprovarMedicaoDialog.tsx` ·
  `frontend/app/(admin)/financeiro/recebimentos/page.tsx` ·
  `frontend/components/modules/financeiro/RecebimentosTable.tsx` ·
  `frontend/lib/hooks/use-medicoes.ts` · `use-recebimentos.ts` ·
  `frontend/e2e/financeiro-medicao.spec.ts`
- **Escopo:** US-F03, US-F04, US-F10.
- **Fora de escopo:** o cálculo do valor liberado *(RN-F06 é backend, S-F7 — a tela **exibe** o valor
  que a API devolve e não o recalcula; duas implementações da mesma fórmula divergem)*; régua de
  cobrança; baixa de recebimento em lote; sidebar *(S-F11)*.
- **Critérios de aceite:**
  - [ ] O formulário mostra o acumulado da medição anterior ao lado do campo (positivo)
  - [ ] Valor abaixo do anterior é barrado no client com mensagem clara
  - [ ] A aprovação pede confirmação mostrando o valor que será liberado
  - [ ] Medição aprovada abre em leitura, sem controles de edição
  - [ ] Papel sem permissão de aprovar não vê o botão **e** a rota recusa — os dois, porque
        esconder o botão não é autorização
  - [ ] axe-core sem violação crítica

### Sprint S-F10 — Telas de análise

- **Agente:** nextjs-developer
- **Depende de:** S-F2 · **Paralela com:** S-F7, S-F8, S-F9
- **Revisor de segurança:** não · **Status:** pendente · **Ciclos:** 0/3 · **Revisores OK:** —
- **Arquivos:**
  `frontend/app/(admin)/obras/[id]/financeiro/page.tsx` ·
  `frontend/app/(admin)/financeiro/page.tsx` ·
  `frontend/components/modules/financeiro/OrcadoRealizadoTable.tsx` ·
  `CurvaSChart.tsx` · `FluxoCaixaChart.tsx` · `AlertaEstouroBadge.tsx` ·
  `frontend/lib/hooks/use-analise-financeira.ts` ·
  `frontend/e2e/financeiro-analise.spec.ts`
- **Escopo:** US-F11, US-F12, US-F13. Gráficos em **SVG inline**, seguindo o padrão de
  `BdiTab.tsx` — não há biblioteca de gráfico no projeto e introduzir uma pressionaria o teto de
  bundle ([ESPEC §10](ESPEC.md#10-frontend)). `frontend/package.json` **não** está na lista de
  arquivos justamente por isso: se a sprint concluir que precisa de dependência nova, **reporte
  em vez de adicionar**.
- **Fora de escopo:** os agregados *(são da S-F9 — a tela consome o endpoint e não soma nada no
  client)*; exportação *(S-F11)*; sidebar *(S-F11)*; qualquer dependência nova de `package.json`.
- **Critérios de aceite:**
  - [ ] A tabela mostra orçado, realizado, comprometido, saldo e % consumido por fase (positivo)
  - [ ] Fase estourada é distinguível **sem depender de cor** — ícone ou rótulo (CA-F11.2)
  - [ ] A Curva S desenha as três séries, distinguíveis por traço e marcador, com legenda
  - [ ] O período corrente é destacado
  - [ ] Obra sem orçamento aprovado mostra empty específico, não zeros (CA-F11.4)
  - [ ] Obra sem cronograma mostra empty com CTA para criar
  - [ ] Valores formatados em pt-BR via `Decimal`
  - [ ] axe-core sem violação crítica nas três telas
  - [ ] Os gráficos têm alternativa textual acessível (tabela ou descrição)

---

## Onda 4

### Sprint S-F11 — Hardening, anexo de NF, exportação e liberação

- **Agente:** backend-developer + nextjs-developer (coordenados)
- **Depende de:** S-F9, S-F10
- **Paralela com:** —
- **Revisor de segurança:** sim (é a sprint que abre o módulo)
- **Status:** pendente · **Ciclos:** 0/3 · **Revisores OK:** —
- **Slot de migration:** — (sem tabela nova)
- **Arquivos:**
  `backend/app/modules/financeiro/routers/despesas.py` *(anexo + export)* ·
  `backend/app/modules/financeiro/services/export.py` ·
  `backend/tests/test_financeiro_export.py` · `test_financeiro_portal_fence.py` ·
  `backend/tests/test_financeiro_papeis.py` ·
  `frontend/components/modules/financeiro/AnexoNfField.tsx` ·
  `frontend/components/modules/financeiro/ExportButton.tsx` ·
  **`frontend/components/shared/Sidebar.tsx`** *(habilitar "Financeiro" — só aqui)* ·
  **`frontend/app/(admin)/obras/[id]/layout.tsx`** *(abas da obra: hoje só `documentos` e
  `equipes`; sem isto, cronograma, medições e financeiro da obra ficam acessíveis só por URL
  digitada)* ·
  `frontend/e2e/financeiro-*.spec.ts` · `frontend/e2e/a11y.spec.ts` ·
  `docs/modulo-financeiro/*.md` *(atualizar o que divergiu durante a execução)*
- **Escopo:** anexo de NF reaproveitando o GED (US-F07); exportação CSV com teto de 10.000 linhas
  (US-F14); varredura de segurança; habilitar o item da sidebar.
- **Fora de escopo:** gate de tier — depende de `require_tier`, que não existe no projeto
  ([ESPEC §9](ESPEC.md#9-autorização)).
- **Critérios de aceite:**
  - [ ] Anexar NF vincula um `documento` existente com tipo `nota_fiscal` da mesma obra
        (positivo); a despesa mostra o anexo e o link assinado funciona
  - [ ] Remover o anexo desfaz o vínculo e **não** apaga o documento
  - [ ] Exportação respeita os filtros e traz obra, fase, categoria, fornecedor, datas, valor e
        status
  - [ ] Exportação com 10.001 linhas devolve 422 pedindo filtro mais estreito — não pendura o
        request
  - [ ] Valores do CSV em pt-BR, calculados com `Decimal`; `1234.565` sai como `1.234,57`
  - [ ] **Nenhuma rota de portal expõe dado financeiro** — teste que varre as rotas de portal
        (SEC-F06, RN-F11)
  - [ ] Matriz de papéis testada rota a rota: `campo`, `viewer` e `ai` recebem 403 em todas
        (SEC-F05)
  - [ ] Recurso de outro tenant devolve 404 em todas as rotas (SEC-F04)
  - [ ] `check_schema_financeiro.py` verde para as nove tabelas
  - [ ] Suíte E2E do módulo verde, desktop e mobile
  - [ ] Item "Financeiro" da sidebar navega e fica ativo
  - [ ] **As telas por obra são alcançáveis pela navegação**, não só por URL: cronograma,
        medições e financeiro aparecem nas abas da obra
  - [ ] A tela de categorias é alcançável — o item "Configurações" da sidebar está
        `disabled` hoje. Se habilitá-lo estiver fora de escopo, **reporte**: a tela da S-F4
        nasce inalcançável
  - [ ] `make test && make lint && make check-contract` verdes; bundle dentro do teto

---

## Cobertura — US → CA → sprint

Requisito sem sprint é escopo perdido; sprint sem requisito é escopo inventado.

Os critérios estão escritos por extenso, um a um, e não como faixa (`CA-F04.1–7`). A faixa economiza
três caracteres e custa a rastreabilidade inteira: quem busca `CA-F04.6` neste arquivo não acha nada,
conclui que o critério não tem sprint, e ou o reimplementa ou o descarta. **Esta tabela já estava
errada por causa disso** — declarava `CA-F04.1–5` depois que a US-F04 ganhou dois critérios novos, e
os dois perdidos eram justamente os que protegem a fórmula de faturamento da RN-F06.

| US | Critérios | Sprint |
|---|---|---|
| US-F01 Gerar cronograma | CA-F01.1, CA-F01.2, CA-F01.3, CA-F01.4, CA-F01.5 | S-F5, S-F6 |
| US-F02 Ajustar distribuição | CA-F02.1, CA-F02.2, CA-F02.3, CA-F02.4 | S-F5, S-F6 |
| US-F03 Registrar medição | CA-F03.1, CA-F03.2, CA-F03.3, CA-F03.4, CA-F03.5 | S-F7, S-F8 |
| US-F04 Aprovar e liberar | CA-F04.1, CA-F04.2, CA-F04.3, CA-F04.4, CA-F04.5, **CA-F04.6**, **CA-F04.7** | S-F7, S-F8 |
| US-F05 Categorias | CA-F05.1, CA-F05.2, CA-F05.3, CA-F05.4 | S-F3, S-F4 |
| US-F06 Lançar despesa | CA-F06.1, CA-F06.2, CA-F06.3, CA-F06.4, CA-F06.5, CA-F06.6 | S-F3, S-F4 |
| US-F07 Anexar NF | CA-F07.1, CA-F07.2, CA-F07.3, CA-F07.4 | S-F11 |
| US-F08 Parcelar | CA-F08.1, CA-F08.2, CA-F08.3, CA-F08.4 | S-F3, S-F4 |
| US-F09 Pagamento | CA-F09.1, CA-F09.2, CA-F09.3, CA-F09.4 | S-F3, S-F4 |
| US-F10 Contas a receber | CA-F10.1, CA-F10.2, CA-F10.3 | S-F7, S-F8 |
| US-F11 Orçado × realizado | CA-F11.1, CA-F11.2, CA-F11.3, CA-F11.4, CA-F11.5, CA-F11.6 | S-F9, S-F10 |
| US-F12 Curva S | CA-F12.1, CA-F12.2, CA-F12.3, CA-F12.4, CA-F12.5 | S-F9, S-F10 |
| US-F13 Fluxo de caixa | CA-F13.1, CA-F13.2, CA-F13.3, CA-F13.4 | S-F9, S-F10 |
| US-F14 Exportar | CA-F14.1, CA-F14.2, CA-F14.3 | S-F11 |
| RN-F03 Fase estável | — | **S-F1** |
| SEC-F01, F02, F03 | — | S-F1, S-F3, S-F5, S-F7 |
| SEC-F04, F05, F06, F07 | — | S-F11 |
| RNF-F01, F02 | — | S-F9 |
| RNF-F03 sem `float` | — | S-F2, S-F3 |
| RNF-F05 a11y | — | S-F4, S-F6, S-F8, S-F10, S-F11 |

Nenhuma US sem sprint. Nenhuma sprint sem US ou requisito — a S-F1 e a S-F2 existem para RN-F03
e para o contrato, que são requisitos de [ESPEC §4](ESPEC.md#4-fase-como-identidade-da-obra) e
[§6](ESPEC.md#6-contratos-de-api).

---

## Pré-requisitos fora deste plano

| Pendência | Efeito | Sprint que destrava |
|---|---|---|
| `require_tier` não existe | O módulo fica aberto a todos os planos | Fora deste plano — pré-requisito de **lançamento comercial**, não de funcionamento |
| US-03 fornecedor não existe | Fornecedor é texto livre ([ESPEC §8](ESPEC.md#8-fornecedor-sem-cadastro)) | Fora deste plano |
| US-16 versionamento não existe | A reconciliação da S-F1 só é exercitada por teste | Fora deste plano |
| Job runner não existe | Exportação é síncrona com teto | Fora deste plano |

Nenhuma delas bloqueia a execução. Todas precisam estar decididas antes de abrir o módulo para
cliente pagante.

---

*SPRINTS Módulos 5 e 6, versão 1.0. Os slots de migration pressupõem a `0031` como última
aplicada — confira antes de criar a `0032`.*
