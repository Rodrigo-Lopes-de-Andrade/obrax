# ESPEC — Módulos 5 e 6: Planejamento Físico-Financeiro e Financeiro

**Versão:** 1.0 | **Data:** 2026-11-02
**Consome:** [PRD do módulo](PRD.md)
**Produz:** [Dicionário de Dados](DICIONARIO-DE-DADOS.md) → [SPRINTS](SPRINTS.md)
**Base de código verificada:** `main` em `89593a5`

---

## 1. Fronteira deste documento

Este documento responde **como**. O que e por quê estão no [PRD do módulo](PRD.md); a semântica
de cada coluna está no [Dicionário](DICIONARIO-DE-DADOS.md).

Decisões de plataforma que **não** se repetem aqui porque já valem no projeto inteiro:
multi-tenancy por RLS, autenticação JWT, convenções de API, storage por URL assinada,
observabilidade. Quando este módulo depender de uma delas, a seção cita a fonte em vez de
copiar — duas cópias divergem.

---

## 2. O que foi verificado, e o que não dá para confiar

A documentação base do projeto está defasada. Este módulo foi desenhado contra o **código**, não
contra ela. O que foi conferido no repositório em 2026-11-02:

| Verificado | Resultado |
|---|---|
| Existe algo financeiro no código? | Não. Módulo greenfield |
| `orcamento_item` tem hierarquia com fases? | Sim: `tipo CHAR(1)` com `'F'`/`'S'`/`'I'`, mais `parent_id`, `path`, `depth` |
| `orcamento_versao` tem o orçado? | Sim: `custo_direto`, `preco_venda`, `markup_global`, `taxa_adm`, `is_locked`, `numero` |
| `obras` tem contrato e datas? | Sim — **e as três são `nullable`**: `valor_contrato NUMERIC(18,2)`, `data_inicio`, `data_prevista_fim`. O docstring da 0009 justifica: obra em planejamento pode não ter datas. Ver [§4.4](#44-os-casos-de-borda-que-o-schema-permite) |
| `orcamento_versao` tem `status`? | **Não.** Só `is_locked` e `numero`. O status vive em `orcamento` — ver [§4.2](#42-o-que-é-uma-versão-aprovada) |
| `orcamento_item.codigo` é obrigatório e único? | **Não.** `nullable=True`, sem índice único. O importador XLSX aceita nulo explicitamente — ver [§4.3](#43-o-código-da-fase-quando-não-há-código) |
| Quantos pontos de aprovação de orçamento existem? | **Dois** — ver [§4.1](#41-onde-a-sincronização-é-disparada) |
| `make check-contract` existe? | **Não.** Escrito em 2026-08-28 e nunca mergeado. A definição de concluído deste plano é `make test && make lint` |
| `MoneyInput` existe no frontend? | **Não.** Mesma origem. A S-F4 o cria |
| Há biblioteca de gráfico? | **Não.** Gráficos são SVG inline (`BdiTab.tsx`) |
| GED aceita nota fiscal? | Sim: enum `documento_tipo` já inclui `'nota_fiscal'` |
| Existe cadastro de fornecedor? | **Não** — ver [§8](#8-fornecedor-sem-cadastro) |
| Existe versionamento de orçamento (US-16)? | **Não** — ver [§4](#4-fase-como-identidade-da-obra) |
| Como o `app_user` ganha acesso a tabela nova? | `ALTER DEFAULT PRIVILEGES` na migration 0001 — ver [§7.3](#73-grant) |
| Qual o predicado correto de RLS? | `app_current_company_id()`, **não** o cast cru — ver [§7.2](#72-o-template-antigo-e-o-que-ele-realmente-causa) |

### Divergências herdadas — não mascarar

A ESPEC 1.0 e o SPRINTS 1.0 do projeto afirmam coisas que o código não faz. Importa aqui porque
este módulo seria desenhado errado se confiasse nelas:

| Documento base | Afirma | Realidade no código |
|---|---|---|
| ESPEC 1.0 §2.1, CLAUDE.md | Job runner Arq, filas `pdf.generate`/`export.generate` | `arq` não está nas dependências; não existe `app/jobs/`. **Consequência aqui:** a exportação CSV deste módulo é síncrona ([§6.4](#64-exportação)) |
| SPRINTS 1.0 S5 | "Versioning linkado (rev 1, rev 2)" como critério cumprido | US-16 não implementada. **Consequência aqui:** [§4](#4-fase-como-identidade-da-obra) |
| ESPEC 1.0 §13, CLAUDE.md | Módulo restrito por tier via flag | Não existe `require_tier`; `/feature-flags` devolve `true` fixo. **Consequência aqui:** [§9](#9-autorização) |
| ESPEC 1.0 §2.1 | LangGraph + Claude Sonnet nos agentes | Não há LLM. Sem consequência para este módulo |

**Fonte de verdade para este módulo: o código.** Quem for atualizar a documentação base
encontra o levantamento completo no histórico da auditoria de 2026-08-28.

---

## 3. Arquitetura

### 3.1 Um módulo, não dois

Módulos 5 e 6 vivem em `app/modules/financeiro/`, com submódulos por domínio:

```
app/modules/financeiro/
  __init__.py
  routers/      __init__.py · cronograma.py · medicao.py · despesas.py
                recebimentos.py · categorias.py · analise.py
  services/     __init__.py · fases.py · cronograma.py · medicao.py · despesas.py
                faturamento.py · orcado.py · curva_s.py · fluxo_caixa.py · export.py
  schemas/      __init__.py — Pydantic, fonte da verdade do contrato
```

**Sem subpacote `models/`.** Verificado: nenhum módulo do projeto tem um, e nenhum service
importa modelo ORM — os 24 services de `app/modules/` usam `text()` parametrizado. Modelo criado
aqui e não registrado em `app/models/__init__.py` ficaria fora do `target_metadata` do Alembic e
seria código morto que nenhum teste valida. As tabelas recentes do projeto (`orcamento*`,
`photo`, `checklist_item`, `lgpd_request`) não têm modelo — este módulo segue o padrão real.

Separar em dois módulos Python criaria uma fronteira que o domínio não tem: a Curva S lê
cronograma (M5) e despesa (M6) na mesma query, e a medição (M5) escreve título a receber (M6).

### 3.2 Decisões fechadas

| Tema | Decisão | Consequência aceita |
|---|---|---|
| Origem do realizado | Lançamento manual de despesa | Adesão depende de disciplina do usuário. Risco registrado no PRD §10; mitigado por formulário curto e parcelamento automático |
| Apropriação | Fase obrigatória, via entidade própria da obra | Uma tabela e uma etapa de reconciliação a mais. Sem isso, revisão de orçamento orfana o histórico ([§4](#4-fase-como-identidade-da-obra)) |
| Orçado | Derivado por agregação da versão aprovada, **não** copiado | Query a cada leitura em vez de coluna desnormalizada. Evita a classe inteira de bug "snapshot desatualizado". Custo medido em [§6.5](#65-desempenho) |
| Alerta de estouro | Calculado na leitura, não persistido | Nada de job nem de coluna que envelhece. O alerta é sempre o estado atual |
| Comprometido | Despesa `prevista` conta para o alerta, separada do realizado | Dois números na tela em vez de um. É a diferença entre decisão reversível e irreversível (PRD RN-F04) |
| Percentuais | `NUMERIC(7,4)` como fração (0,1500 = 15%) | Conversão na apresentação. Evita a ambiguidade 15 vs 0,15 que aparece em toda base que mistura os dois |
| Medição | Cumulativa e imutável após aprovação | Correção exige medição de ajuste. É o que torna o par medição/título uma trilha de aceite |
| Exportação | Síncrona, com teto de linhas | Não há job runner. Teto explícito e erro claro acima dele ([§6.4](#64-exportação)) |
| Moeda | BRL implícita, sem coluna de moeda | Multi-moeda está fora de escopo |

---

## 4. Fase como identidade da obra

É a decisão estrutural deste módulo. Errar aqui custa o histórico financeiro inteiro na primeira
revisão de orçamento.

### O problema

A despesa precisa apontar para uma fase. O candidato natural é `orcamento_item` com `tipo='F'`.
Mas criar a revisão 2 de um orçamento **clona os itens**, gerando IDs novos (é o que a US-16 vai
fazer). Toda despesa apontando para itens da revisão 1 ficaria órfã, e o orçado × realizado
mostraria uma obra sem gasto nenhum — **silenciosamente**, porque um `LEFT JOIN` que não casa
devolve zero, não erro.

### A decisão

Uma entidade própria: `obra_fase`. É a lista canônica de fases **da obra**, com identidade
estável. Despesa, cronograma e medição referenciam `obra_fase`. Versões de orçamento se
reconciliam nela por `codigo`.

```
orcamento_versao (aprovada)  ──sincroniza──►  obra_fase  ◄── despesa
      itens tipo='F'                              ▲        ◄── cronograma_alocacao
                                                  └──────  ◄── medicao_item
```

**Quando sincroniza:** na aprovação de uma versão. Fase com código novo é criada; código
existente tem descrição e valor orçado atualizados; código que sumiu é marcado inativo, **nunca
apagado** — pode ter despesa.

**O que o usuário vê:** ao aprovar uma versão que remove fases com despesa lançada, a tela lista
as fases afetadas e pede confirmação. Reconciliação silenciosa aqui é como o histórico se perde
sem ninguém notar.

### Alternativas descartadas

| Alternativa | Por que perdeu |
|---|---|
| Despesa aponta direto para `orcamento_item` | Quebra na primeira revisão, e quebra em silêncio |
| Despesa guarda `obra_id` + `fase_codigo` em texto | Sem integridade referencial; renomear código órfana; nenhuma forma de marcar fase inativa |
| Congelar o orçamento ao criar a primeira despesa | Transfere o problema para o usuário, que perde a capacidade de revisar — justamente a US-16 |

### 4.1 Onde a sincronização é disparada

Existem **dois** pontos de aprovação no código, e os dois precisam do hook:

| Caminho | Arquivo | Quem usa |
|---|---|---|
| `PATCH /orcamentos/{id}/status` → `aprovado` | `app/modules/orcamento/services/orcamentos.py` | O admin, pelo painel |
| Aprovação pelo portal, com assinatura | `app/modules/portal/service.py` *(`UPDATE orcamento SET status`)* | **O cliente — é o fluxo da US-18** |

> **Cabear só o primeiro é a falha mais cara deste plano.** Na operação real o cliente aprova
> pelo portal. Sem o hook ali, `obra_fase` nasce vazia, `despesa.obra_fase_id NOT NULL` torna
> impossível lançar qualquer despesa, e a tela de orçado × realizado mostra para sempre o empty
> state de "obra sem orçamento aprovado" — que é **exatamente** o estado que o CA-F11.4 manda
> exibir. Falha em silêncio, com todos os critérios verdes.
>
> A extração é um service único chamado pelos dois caminhos, e o teste exercita **as duas
> rotas**, não o service.

### 4.2 O que é uma "versão aprovada"

`orcamento_versao` **não tem coluna `status`** — verificado. O status vive em `orcamento`, e
todo o projeto resolve a versão vigente por
`JOIN orcamento_versao v ON v.orcamento_id = o.id AND v.numero = o.versao_atual` (7 ocorrências).

**Decisão:** a versão de referência deste módulo é
`v.numero = o.versao_atual AND o.status = 'aprovado'`. `is_locked` **não** é o predicado: ele
marca snapshot imutável e é setado também pelo portal, mas não distingue aprovado de rejeitado.

### 4.3 O código da fase quando não há código

`orcamento_item.codigo` é `nullable` e sem unicidade; o importador XLSX exige apenas `tipo` e
`descricao`. Como `obra_fase.codigo` é `NOT NULL` e a chave de reconciliação, dois casos quebram
o INSERT:

| Caso | Decisão |
|---|---|
| Fase sem código | Código sintético `F{sort_order:03d}` — estável enquanto a ordem não muda, e a ordem é a do orçamento |
| Duas fases com o mesmo código na mesma versão | **Recusa a aprovação** com 422 nomeando as fases. Não deduplicar em silêncio: duas fases homônimas são ambiguidade de orçamento, e escolher uma delas apropriaria despesa na fase errada |

O código sintético é um compromisso conhecido: renomear a ordem das fases entre versões
desloca o casamento. A alternativa — exigir código no orçamento — mudaria o Módulo 2 e está
fora deste escopo. Registrado como risco no PRD §10.

### 4.4 Os casos de borda que o schema permite

`obras.valor_contrato`, `data_inicio` e `data_prevista_fim` são **nullable** por decisão da
migration 0009. Consequências, todas com critério próprio:

| Nulo | Efeito | Decisão |
|---|---|---|
| `valor_contrato` | RN-F06 multiplica por ele | Medição aprova **sem gerar título**, com aviso (CA-F04.7) |
| `data_inicio` ou `data_prevista_fim` | Não há como gerar os períodos | `POST /cronograma` devolve **422** nomeando a data que falta — não 500 |

### 4.5 Enquanto a US-16 não existir

O desenho funciona igual: há uma versão só, a sincronização roda na aprovação dela, e a
reconciliação nunca encontra divergência.

Mas o critério central da S-F1 — aprovar uma **segunda** versão e manter o mesmo `id` — **não tem
caminho de código**: `aprovado` é estado terminal (`"aprovado": set()` em `_TRANSICOES`), o único
`INSERT INTO orcamento_versao` grava `numero` literal `1`, e nada faz `UPDATE … SET versao_atual`.

A fixture monta a versão 2 por SQL direto, bumpa `versao_atual` e chama o service de
sincronização. O teste então valida a reconciliação, **não** o disparo — e o SPRINTS diz isso
explicitamente, para ninguém confundir cobertura de um com a do outro.

---

## 5. Modelo de domínio

```
obra ──┬── obra_fase ──┬── despesa ──► documento (NF, opcional)
       │               ├── cronograma_alocacao
       │               └── medicao_item
       ├── cronograma ──── cronograma_periodo
       ├── medicao ─────── medicao_item
       └── recebimento ◄── medicao (aprovada)

company ── categoria_financeira ──► despesa
```

Nove tabelas novas. Colunas, constraints, índices e policies no
[Dicionário de Dados](DICIONARIO-DE-DADOS.md).

### Máquinas de estado

```
despesa:      prevista ──pagar──► paga ──desfazer──► prevista
                  └──cancelar──► cancelada        (cancelada é terminal)

medicao:      rascunho ──aprovar──► aprovada      (aprovada é terminal; correção = nova medição)

recebimento:  previsto ──receber──► recebido ──desfazer──► previsto
```

Transição não listada é erro 422 com a transição válida na mensagem. Nenhuma delas é inferida de
data — status é explícito, porque "está pago porque a data passou" é como um sistema financeiro
mente.

---

## 6. Contratos de API

Convenções do projeto (UUID v7, cursor, ISO 8601, RFC 7807): ver [ESPEC principal §6](../ESPEC.md).
Prefixo `/api/v1`. Todas exigem JWT e papel autorizado ([§9](#9-autorização)).

### 6.1 Planejamento

```
POST   /obras/{obra_id}/cronograma              cria a partir da versão aprovada
GET    /obras/{obra_id}/cronograma              grade fase × período
PUT    /cronograma/{id}/alocacoes               ajusta a distribuição (bulk)

GET    /obras/{obra_id}/medicoes                lista
POST   /obras/{obra_id}/medicoes                cria rascunho para um período
GET    /medicoes/{id}                           detalhe com itens
PUT    /medicoes/{id}/itens                     grava os percentuais (bulk)
POST   /medicoes/{id}/aprovar                   imutabiliza e gera o recebimento
```

### 6.2 Financeiro

```
GET,POST   /financeiro/categorias               plano de contas da empresa
PATCH      /financeiro/categorias/{id}          renomear, ativar, desativar

GET,POST   /obras/{obra_id}/despesas            lista e lança
GET,PATCH,DELETE /financeiro/despesas/{id}
POST       /financeiro/despesas/{id}/pagar      { data_pagamento }
POST       /financeiro/despesas/{id}/estornar
POST       /obras/{obra_id}/despesas/parcelada  gera N títulos numa transação

GET        /financeiro/recebimentos             filtro por obra e status
POST       /financeiro/recebimentos/{id}/receber
```

### 6.3 Análise

```
GET /obras/{obra_id}/financeiro/orcado-realizado   por fase, com comprometido e alerta
GET /obras/{obra_id}/financeiro/curva-s            três séries acumuladas por período
GET /financeiro/fluxo-caixa?obra_id=&de=&ate=      previsto × realizado por período
GET /obras/{obra_id}/financeiro/export.csv         ver §6.4
```

**`PUT` em dois lugares** (`/alocacoes`, `/itens`) porque a operação substitui o conjunto
inteiro, não altera um item. Enviar a grade parcial causaria estado meio gravado, e a
RN-F07 (fechar 100%) só é verificável sobre o conjunto completo.

### 6.4 Exportação

Síncrona, porque **não existe job runner** ([§2](#2-o-que-foi-verificado-e-o-que-não-dá-para-confiar)).
Teto de **10.000 linhas**; acima disso devolve 422 pedindo que o filtro seja estreitado. Um
teto explícito com erro claro é preferível a um request que pendura um thread do Gunicorn — o
mesmo débito que já afeta o PDF do orçamento.

Quando o job runner existir, esta rota migra para 202 + polling, como as demais.

### 6.5 Desempenho

O orçado é agregado a cada leitura, não desnormalizado. Para o alvo do RNF-F01 (50 fases,
2000 despesas, < 1s):

- `obra_fase` guarda `valor_orcado`, preenchido na sincronização — a agregação sobre
  `orcamento_item` acontece **uma vez por aprovação de versão**, não a cada leitura. É
  desnormalização de um valor que só muda num evento conhecido, e não a cada despesa.
- Realizado e comprometido saem de **uma** query com `GROUP BY obra_fase_id` e `FILTER` por
  status — não N+1 por fase.
- Índice `(company_id, obra_id, obra_fase_id, status)` em `despesa` cobre essa agregação.

Benchmark com seed desse tamanho entra como teste, não como medição manual.

---

## 7. Isolamento multi-tenant

É o ponto de maior acoplamento do projeto, e a área onde documentação plausível causa
vazamento. As três sub-seções abaixo existem porque cada peça que falta produz uma falha
**diferente**, e três das quatro falham **abrindo**.

### 7.1 O mecanismo completo

1. `TenantMiddleware` decodifica o JWT e popula o contexto.
2. `get_db` abre a transação e executa `SET LOCAL app.company_id`.
3. Cada tabela tem `company_id NOT NULL` denormalizado.
4. `ENABLE ROW LEVEL SECURITY` **e** `FORCE ROW LEVEL SECURITY` — sem o `FORCE`, o dono das
   tabelas ignora a policy.
5. Policy com `USING` **e** `WITH CHECK` — só `USING` deixa escrita cruzar a fronteira, e o
   teste de isolamento, que só lê, fica verde.
6. A API roda como `app_user`, jamais como `app_admin`.

Falta o passo 2 ou o 4 → devolve tudo, sem erro. Falta o 5 → escrita cruza. Falta o `GRANT` →
erro barulhento, que é o caso bom.

### 7.2 O template antigo e o que ele realmente causa

A migration 0023 escreve o predicado assim:

```sql
-- ❌ NÃO COPIAR: padrão anterior à 0030
USING (company_id = current_setting('app.company_id', true)::uuid)
```

**Medido, não deduzido** ([§7.6](#76-o-que-foi-medido)): com `app.company_id` vazio (string
`''`), esse predicado **não vaza** — ele levanta
`ERROR: invalid input syntax for type uuid: ""`. O request morre com 500 em vez de devolver
negação limpa. É fail-closed, porém barulhento e quebrado.

O helper da 0030 transforma esse 500 numa negação correta — zero linhas — porque faz
`NULLIF(..., '')` antes do cast. É a razão de usá-lo, e **não** é "o cast cru vaza":



```sql
-- ✅ padrão vigente, desde a 0030
USING (company_id = app_current_company_id())
WITH CHECK (company_id = app_current_company_id())
```

`app_current_company_id()` faz `NULLIF(current_setting('app.company_id', true), '')::uuid` e tem
`search_path` fixado.

> **O template de tabela nova está no [Dicionário §2](DICIONARIO-DE-DADOS.md). Use aquele.**

### 7.3 GRANT

A migration 0001 configurou `ALTER DEFAULT PRIVILEGES IN SCHEMA public` concedendo
`SELECT, INSERT, UPDATE, DELETE` a `app_user` e `app_admin`. Tabela nova criada pela migration
herda o privilégio — **desde que criada pelo mesmo papel** que configurou o default.

Não é uma garantia que se possa assumir: a verificação automatizada ([§11](#11-estratégia-de-teste))
confere privilégio no catálogo, tabela a tabela. Falta de `GRANT` falha barulhento, mas falha
tarde — em runtime, no primeiro uso.

### 7.4 Views — a falha silenciosa de verdade

Esta é a única peça do mecanismo que, nas medições de [§7.6](#76-o-que-foi-medido), **vazou dado
de outro tenant sem erro nenhum**.

View sobre tabela protegida executa com privilégio do dono e ignora a RLS, a menos que declare
`security_invoker = true`. Medido: a view sem a opção devolveu as linhas dos **dois** tenants
para um usuário de um só; a view com a opção devolveu apenas as do tenant corrente.

E a verificação automatizada que percorre **tabelas** não enxerga views — precisa de item
próprio ([Dicionário §6](DICIONARIO-DE-DADOS.md), consulta 4, que foi executada e detectou
corretamente uma view criada sem a opção).

**Decisão deste módulo: nenhuma view.** As agregações são queries no service, parametrizadas.
Se uma view aparecer depois, esta seção é o contrato que ela precisa cumprir.

### 7.5 Erro que revela existência

Recurso de **outro tenant** → **404**. Sem permissão **dentro** do próprio tenant → **403**.
Um 403 em recurso de outro tenant confirma que ele existe.

Na prática, com RLS ativa o `SELECT` já devolve zero linhas e o 404 sai natural — o cuidado é
não "melhorar" isso para 403 achando que é mais informativo.

### 7.6 O que foi medido

As afirmações de [§7.2](#72-o-template-antigo-e-o-que-ele-realmente-causa) e
[§7.4](#74-views--a-falha-silenciosa-de-verdade) vêm de execução contra PostgreSQL, com duas
tabelas idênticas diferindo só no predicado, e não de leitura da documentação do Postgres.
Primeira redação deste documento afirmava que três das peças falhavam abrindo; a medição derrubou
duas dessas três.

| Peça ausente | Comportamento medido | Modo de falha |
|---|---|---|
| `FORCE ROW LEVEL SECURITY` | O **dono** da tabela leu as linhas dos dois tenants | 🔴 **Abre, em silêncio** |
| `security_invoker` numa view | A view devolveu as linhas dos dois tenants | 🔴 **Abre, em silêncio** |
| Helper, usando o cast cru, contexto vazio | `ERROR: invalid input syntax for type uuid: ""` | 🟡 Fecha, com 500 |
| `WITH CHECK` numa policy `FOR ALL` | Escrita cross-tenant **recusada** — o Postgres usa o `USING` como check | 🟢 Fecha |
| `GRANT` | `ERROR: permission denied` | 🟢 Fecha, barulhento |

**Consequências para quem executa:**

1. `FORCE` não é formalidade. A API roda como `app_user`, que não é dono — mas migration, script
   e sessão de debug rodam como dono, e é aí que o vazamento aparece sem erro.
2. **Nenhuma view sobre tabela do módulo**, e a checagem de view é item separado.
3. `WITH CHECK` continua obrigatório no template — não porque a ausência abra numa policy
   `FOR ALL`, mas porque torna a intenção explícita e protege contra alguém restringir a policy a
   `FOR SELECT` depois.
4. O teste de isolamento precisa do **positivo**: as duas tabelas do experimento passariam em
   qualquer teste só-negativo, inclusive a que vaza.

---

## 8. Fornecedor sem cadastro

A US-03 não foi implementada. Decisão:

- `despesa.fornecedor_nome TEXT NOT NULL` — o que o usuário digita hoje
- `despesa.fornecedor_id UUID NULL` — a coluna de vínculo, já criada, sem FK enquanto a tabela
  não existir

Quando a US-03 chegar, uma migration de reconciliação liga por documento, depois por nome
exato normalizado, e **apresenta os ambíguos** em vez de adivinhar. O autocomplete do formulário
passa a sugerir fornecedores cadastrados, mantendo texto livre como fallback.

Criar `fornecedores` dentro deste módulo foi descartado: é escopo do Módulo 1, e a tabela
nascendo aqui teria o recorte do financeiro, não o do cadastro.

---

## 9. Autorização

| Papel | Acesso |
|---|---|
| `owner`, `admin` | Tudo |
| `financeiro` | Tudo, exceto aprovar medição |
| `gestor` | Leitura de tudo; cria despesa; **não** aprova medição nem registra pagamento |
| `orcamentista` | Leitura de orçado × realizado e Curva S |
| `campo`, `viewer`, `ai` | **Nenhum acesso** |

Aprovar medição é ato comercial com o cliente — fica com `owner`/`admin`.

**Tier:** o PRD §9 coloca o módulo em Pro e Enterprise. `require_tier` **não existe** no código.
Enquanto não existir, o módulo fica disponível em todos os planos, como o Módulo 3. A dependência
está registrada no [SPRINTS](SPRINTS.md) como pré-requisito de lançamento comercial, não de
funcionamento.

**Portal:** nenhuma rota deste módulo é montada no router de portal. A verificação é um teste que
varre as rotas de portal procurando prefixo `financeiro` ou tabela do módulo (PRD RN-F11).

---

## 10. Frontend

```
(admin)/obras/[id]/financeiro          orçado × realizado + alerta  (US-F11)
(admin)/obras/[id]/financeiro/despesas lista e lançamento           (US-F06..F09)
(admin)/obras/[id]/cronograma          grade fase × período         (US-F01, F02)
(admin)/obras/[id]/medicoes            lista, rascunho, aprovação   (US-F03, F04)
(admin)/financeiro                     fluxo de caixa da empresa    (US-F13)
(admin)/financeiro/recebimentos        títulos a receber            (US-F10)
(admin)/configuracoes/categorias       plano de contas              (US-F05)
```

A sidebar tem **"Financeiro" como `disabled`** hoje. Habilitar é parte da última sprint, não da
primeira — item habilitado apontando para tela incompleta é pior que item desabilitado.

**Moeda:** usar `MoneyInput` e os formatadores `Decimal` existentes. `toFixed()` sobre `Number`
em valor financeiro é proibido (PRD RN-F10).

**Curva S e fluxo de caixa:** **não existe biblioteca de gráfico no projeto** — verificado:
nenhum import de Recharts, Chart.js ou similar, e os gráficos atuais (`BdiTab.tsx`,
`ProgressRing.tsx`) são SVG inline escrito à mão. A ESPEC 1.0 afirma Recharts; é mais uma
divergência herdada ([§2](#2-o-que-foi-verificado-e-o-que-não-dá-para-confiar)).

Decisão: **seguir o padrão da casa, SVG inline**. Introduzir uma biblioteca de gráfico custaria
dependência nova e pressionaria o teto de 240 kB por rota, que hoje tem folga de 33 kB. Séries
distinguíveis **sem depender de cor** (CA-F12.2) — traço e marcador diferentes, legenda com
rótulo, e alternativa textual acessível.

**Estados obrigatórios** em toda tela: loading com skeleton, empty com CTA, error com retry.
A tela de orçado × realizado tem um empty **específico** para "obra sem orçamento aprovado"
(CA-F11.4) — zeros ali seriam indistinguíveis de "orçado é zero".

---

## 11. Estratégia de teste

### O que precisa de teste porque falha em silêncio

| Mecanismo | Falha silenciosa possível | Teste |
|---|---|---|
| RLS | Devolve dado de outro tenant sem erro | Isolamento por tabela, leitura **e** escrita |
| RLS com zero policies | Schema "protegido" passa em todo teste negativo | **Teste positivo**: tenant A vê as próprias linhas |
| Reconciliação de fases | Despesa órfã some do relatório como se não existisse | Fixture com duas versões; conferir que a despesa segue na fase certa |
| Agregação do orçado | `LEFT JOIN` sem casar devolve zero, não erro | Caso com valores conferidos à mão |
| Fechamento do cronograma | Soma 99,99% passa por arredondamento | Caso de borda com três casas |
| Monotonia da medição | Percentual menor gravado sem reclamar | Caso que tenta retroceder e espera 422 |
| Soma das parcelas | Arredondamento faz a soma divergir do original | Valor que não divide exato (ex.: 1000,00 em 3) |

### Caça ao falso verde

Para cada critério de aceite: **que implementação errada passa nisto?**

- Critério só-negativo ("A não vê B") fica verde quando **ninguém** vê nada. Por isso
  CA-F11.5 e SEC-F03 existem: são os positivos do conjunto.
- "Alerta não dispara quando está dentro do orçado" fica verde se o alerta nunca disparar. O par
  obrigatório é "dispara quando ultrapassa".
- "Despesa sem fase é recusada" fica verde se nenhuma despesa for gravada. O par é "despesa com
  fase é aceita e aparece na fase certa".

### Verificação automatizada, no mesmo comando dos testes

Consulta ao **catálogo do Postgres**, nunca busca textual no SQL — busca textual não enxerga
tabela criada dentro de bloco anônimo, nem RLS habilitada e desabilitada depois:

- toda tabela do módulo com `relrowsecurity` **e** `relforcerowsecurity`
- toda tabela com policy que tenha `USING` **e** `WITH CHECK`
- toda tabela com privilégio concedido a `app_user`
- nenhuma view sobre tabela do módulo sem `security_invoker`
- nenhum `float` em caminho de cálculo financeiro

### Cobertura

100% nas rotas com checagem de papel e nos services de cálculo. 70% no restante — mesma régua
do projeto.

---

## 12. Rastreabilidade

| Origem | Destino |
|---|---|
| OBJ-F01 | US-F06, US-F11 |
| OBJ-F02 | US-F11, RN-F04 |
| OBJ-F03 | US-F01, US-F03, US-F12 |
| OBJ-F04 | US-F04, US-F10, RN-F06 |
| OBJ-F05 | US-F06, US-F07, RN-F02 |
| RN-F03 | [§4](#4-fase-como-identidade-da-obra), tabela `obra_fase` |
| SEC-F01..F07 | [§7](#7-isolamento-multi-tenant), [§11](#11-estratégia-de-teste) |

A matriz completa US → CA → sprint está no [SPRINTS §Cobertura](SPRINTS.md).

---

*ESPEC Módulos 5 e 6, versão 1.0. Cada afirmação sobre o estado do código foi verificada contra
`main` em `89593a5`; o que não pôde ser verificado está marcado como tal em [§2](#2-o-que-foi-verificado-e-o-que-não-dá-para-confiar).*
