# ERRATA — Módulos 5 e 6

Divergências **encontradas e ainda não resolvidas** entre este plano e o resto do projeto. Cada
uma declara a fonte de verdade. Conflito mascarado é pior que conflito registrado: se um documento
diz A e o outro diz B, alguém implementa os dois.

Resolvida uma entrada, ela sai daqui e a correção vai para o documento de origem.

---

## E-01 · `docs/CLAUDE.md` proíbe as telas que as Ondas 3 e 4 constroem

**Severidade: bloqueia a Onda 3.**

`docs/CLAUDE.md` > *O que NÃO Tocar*:

> Sidebar items "Compras" e "Financeiro" — deixar como `disabled` no MVP V1. Não criar rotas ou
> telas para eles.

E o código está exatamente assim — `frontend/components/shared/Sidebar.tsx:38`:

```tsx
{ label: "Financeiro", icon: Wallet, href: "#", disabled: true },
```

As sprints S-F4, S-F6, S-F8 e S-F10 criam essas rotas e telas; a S-F11 habilita o item.

**Por que isso não é detalhe:** um agente que leia o `CLAUDE.md` como instrução vigente — e é para
isso que ele existe — recusa a tarefa ou a executa e é reprovado por violar *O que NÃO Tocar*. Nos
dois casos a sprint queima ciclos por um conflito de documentação.

**Fonte de verdade: indefinida — precisa de decisão humana.** Duas saídas:

- emendar o `docs/CLAUDE.md`, trocando a proibição por "habilitar só na S-F11
  (`docs/modulo-financeiro/SPRINTS.md`)"; ou
- declarar aqui que, para os Módulos 5 e 6, o `SPRINTS.md` prevalece — e manter a proibição para o
  item "Compras", que continua fora de escopo.

Enquanto não houver decisão, **a Onda 3 não é despachável**.

**Decisão (2026-11-02, humano): emendar o `docs/CLAUDE.md`.** As duas menções em *O que NÃO
Tocar* foram reescritas: "Compras" segue proibido; "Financeiro" é construído pelas sprints deste
plano e o item da sidebar só é habilitado na S-F11, com aprovação humana. **Resolvida — a Onda 3
é despachável.**

---

## E-02 · `docs/CLAUDE.md` manda rodar alvos de `make` que não existem

**Severidade: trava sprint por comando inexistente.**

`docs/CLAUDE.md` > *Setup e Execução* instrui:

```
make gen-types     # openapi-typescript → frontend/lib/api.d.ts
make build         # build produção
```

O `Makefile` não tem nenhum dos dois — e diz, em comentário na própria cabeça do arquivo, que eles
"chegam com as tarefas de frontend/DevOps das próximas sprints". `make check-contract`, citado em
documentação de agosto, também não existe: foi escrito em 2026-08-28 e nunca mergeado.

Alvos que **existem**, verificados um a um: `help`, `up`, `down`, `migrate`, `dev`, `dev-backend`,
`dev-frontend`, `test`, `lint`, `fmt`. E `make test` e `make lint` cobrem **só o backend**.

**Fonte de verdade: o `Makefile`.** Os portões de frontend rodam direto, e os quatro existem em
`frontend/package.json`:

```bash
cd frontend && pnpm lint
cd frontend && pnpm exec tsc --noEmit
cd frontend && pnpm build:budget
cd frontend && pnpm test:e2e
```

O `SPRINTS.md` §"Regras de execução" já reflete isso. Pendência real: ou criar os alvos
(`gen-types`, `build`, e um `check-contract`), ou corrigir o `docs/CLAUDE.md`. O `Makefile` não
está na lista de `Arquivos` de nenhuma sprint deste plano, de propósito — é trabalho de outra
frente.

---

## E-03 · Nome do plano de entrada: "Basic" no produto, `starter` no schema

**Severidade: baixa — cosmética em produto, real em código.**

O PRD principal e o material comercial chamam o plano de entrada de **Basic**. O enum
`company_tier` no banco é `('starter','pro','enterprise')`. A divergência é anterior a este módulo.

**Fonte de verdade: o enum.** Para código, `starter`. Já registrado no
[PRD §9](PRD.md#9-tier).

---

## E-04 · `ObrasTable` não tem coluna de nome da obra

**Severidade: baixa — afeta teste, não funcionalidade.**

Encontrado ao escrever E2E em agosto: `ObrasTable` não exibe o nome da obra, então um teste que
cria uma obra não pode afirmar sobre o nome — afirma sobre o código gerado. Não é defeito deste
módulo e nenhuma sprint dos Módulos 5 e 6 toca essa tabela.

**Fonte de verdade: o código.** Registrado para que quem escrever E2E de obra não perca tempo
procurando a coluna.

---

## E-05 · A baseline "17 vermelhos conhecidos" era vazamento do `.env` de produção

**Severidade: muda o portão de todas as sprints.**

O `.claude/commands/orquestrador-financeiro.md` (§2) manda tolerar 17 vermelhos em
`tests/test_photos_sync.py` e `tests/test_documentos_upload.py`, atribuídos a um defeito do
mock S3 (moto). **Não há moto nos testes:** eles falam com o S3 configurado. O
`backend/app/core/config.py` faz `load_dotenv(.env, override=False)`, e o `.env` da raiz
aponta o storage para **produção**. Rodar `make test` fixando só o `DATABASE_URL` faz esses
testes lerem e gravarem no bucket de produção.

Medido em 2026-11-02, na `main` em `71ac91d`, Postgres/MinIO locais via `docker compose`:

| Ambiente | Resultado |
|---|---|
| Só `DATABASE_URL` local (como a §2 manda) | 10 falhas + 7 erros — inclusive `test_health` (storage de produção = `error`) |
| Todas as integrações fixadas no local (= CI, que não tem `.env`) | **332 passaram · 0 falharam · 0 erros** |

**Decisão (2026-11-02, humano):**
- A baseline real é **332 verdes, 0 vermelhos**. O portão volta a ser "tudo verde": qualquer
  vermelho é regressão da sprint, não um conjunto tolerado. A orientação da §2 do orquestrador
  sobre os 17 vermelhos fica **revogada** por esta errata.
- O vazamento é fechado **antes** da Onda 1, por correção fora do plano (`conftest.py` fixa as
  integrações no local antes de importar a app; `make test`/`make migrate` exigem `DATABASE_URL`
  explícito). Sem ela, todo ciclo de portão das sprints escreveria no storage de produção.

O banco de produção não foi tocado nas medições: as DSNs `APP_*` estão vazias no `.env` e
caíram no `DATABASE_URL` local. Só o storage vazou.

---

## E-06 · Q3 do Dicionário §6 aceitava GRANT parcial

Medido pelo `revisor-isolamento` na S-F1 (2026-11-03): `has_table_privilege(role, tabela,
'SELECT, INSERT, UPDATE, DELETE')` devolve **true se o role tiver qualquer um** dos privilégios.
Com `REVOKE SELECT, INSERT, UPDATE` sobrando só `DELETE`, a consulta dava "ok". O
`check_schema_financeiro.py` copiou a consulta e herdou o furo.

**Decisão (humano): corrigir o Dicionário.** A Q3 do §6 agora checa os quatro privilégios um a
um. Corrigido também no script, na S-F1 (ciclo 1).

---

## E-07 · Uma obra, vários orçamentos — mas `obra_fase` é por obra

Achado do `code-reviewer` na S-F1. O código permite vários orçamentos por obra (não há `UNIQUE`
em `orcamento(obra_id)`; o portal escolhe o mais recente), e a ESPEC §4.5 assume "uma versão só".
Aprovar um **segundo** orçamento da mesma obra inativava as fases do primeiro — e, com códigos
sintéticos, sobrescrevia a fase `F000` de um com a do outro **no mesmo `id`**, transferindo em
silêncio as despesas já apropriadas. Re-aprovar (`aprovado → aprovado`) ressincronizava o estado.

**Decisão (humano, 2026-11-05): um orçamento aprovado por obra.**
- Aprovar um orçamento quando a obra já tem **outro** orçamento `aprovado` é recusado com **409**,
  pelo painel e pelo portal.
- Transição para o mesmo status (`aprovado → aprovado`) não ressincroniza.
- Aditivo é **nova versão do mesmo orçamento** (US-16), não um orçamento novo.
- A sincronização serializa por obra (lock), fechando a corrida entre aprovações concorrentes.

Sem mudança de schema. Implementado na S-F1 (ciclo 1).

**Decorrências (orquestrador, S-F1 ciclo 2 — sinalizadas ao humano):** o `code-reviewer`
reproduziu que excluir (soft-delete) o orçamento aprovado e aprovar outro reabria exatamente o
furo acima (a `F000` de "Fundações" virava "Pintura" no mesmo `id`). Para a regra não ser
contornável: **orçamento `aprovado` não pode ser excluído (409)**; e a ida para
`aguardando_aprovacao` já recusa (409) quando a obra tem outro orçamento aprovado, para o cliente
nunca receber no portal um orçamento que não pode aprovar.

---

## E-08 · Integridade entre tenants no nível do schema (FK sem tenant)

Medido pelo `revisor-isolamento` na S-F1, como `app_user` com a GUC de A:
`INSERT obra_fase(company_id=A, obra_id=<obra de B>)` **passa** — a FK confere a obra sem RLS. E
`UNIQUE (obra_id, codigo)` global vira oráculo de existência de obra de outro tenant (erro de
duplicata).

Hoje **não é alcançável**: o `obra_id` vem do orçamento lido sob RLS e nenhuma rota escreve em
`obra_fase`. Mas a S-F3 (`despesa`) e as seguintes repetem o padrão com rotas de escrita.

**Decisão (humano, 2026-11-05): registrar e decidir antes da S-F3.** Saídas em discussão: FK
composta `(company_id, obra_id) → obras(company_id, id)` (exige `UNIQUE (company_id, id)` em
`obras`) e/ou unicidade com `company_id`. **A Onda 2 não despacha a S-F3 sem essa decisão.**

**Decisão (humano, 2026-11-22): FK composta no banco.** Toda referência de uma tabela do módulo a
uma linha de outra tabela de tenant passa a ser `(company_id, <x>_id) → <pai>(company_id, id)`,
com `UNIQUE (company_id, id)` no pai. Vale para `obras` (pai de `obra_fase` e das tabelas novas),
`obra_fase` (pai de `despesa`, `cronograma_alocacao`, `medicao_item`) e para cada pai novo das
sprints seguintes. A migration `0033` (S-F3) cria `UNIQUE (company_id, id)` em `obras` e troca a
FK de `obra_fase.obra_id` pela composta; `UNIQUE (obra_id, codigo)` de `obra_fase` passa a incluir
`company_id`, para não ser oráculo de existência. Isto substitui as FKs simples do Dicionário
§4 nas tabelas do módulo.

Aplicação na S-F3 (orquestrador, dentro da decisão acima): também ganham `UNIQUE (company_id, id)`
`documento` (pai de `despesa.documento_id`) e `orcamento_versao` (pai de
`obra_fase.orcamento_versao_id`), e essas FKs viram compostas com `ON DELETE SET NULL (<coluna>)`
(PG ≥ 15), porque `SET NULL` sem lista anularia o `company_id` NOT NULL. `users` não é tabela de
tenant (o vínculo fica em `user_company_role`): `created_by → users(id)` continua simples, como
exceção explícita do `check_schema_financeiro.py`.

---

## E-09 · Débitos aceitos no fechamento da S-F1

O `code-reviewer` deu FECHA no ciclo 2 (39 mutantes; todos os relevantes morrem). Ficaram
débitos **não bloqueantes**, sem corrupção de dado — registrados para não se perderem:

1. **Regra de produto, decisão humana pendente:** com dois orçamentos da mesma obra em
   `aguardando_aprovacao`, o painel aprova o mais antigo e o portal (que mostra o mais recente,
   `ORDER BY o.id DESC`) passa a exibir ao cliente um orçamento que ele **não consegue aprovar**
   (409). Saídas: ao aprovar, mover os outros `aguardando` da obra para `em_revisao`; ou o portal
   priorizar o aprovado.
2. Botão "Excluir" aparece para orçamento aprovado (`frontend/.../OrcamentosView.tsx`); a API
   recusa com 409 e o toast mostra o motivo.
3. Mensagem do 409 no portal está escrita para o gestor ("crie uma nova versão"), não para o
   cliente final.
4. Testes: falta corrida exclusão × aprovação (o código é atômico: condição dentro do UPDATE) e
   normalização de código de fase (caixa, `strip`); `_corrida` faz `join` em thread não iniciada se
   o passo que segura o lock falhar.
5. **Sem backfill de `obra_fase`** para obras com orçamento aprovado antes da S-F1; e obras legadas
   com dois aprovados não conseguem aprovar mais nada. **Decidir antes do deploy do backend** (ver
   também a consulta de diagnóstico em produção).

---

## E-10 · Lacunas do contrato da ESPEC §6 fechadas na S-F2

A ESPEC §6 lista as 25 operações, mas não os corpos. O `fastapi-developer` da S-F2 propôs, e o
humano aprovou em 2026-11-12, como **contrato oficial** (`backend/app/modules/financeiro/schemas/`):

- **`DELETE /financeiro/despesas/{id}` = cancelar**: `status → cancelada` (terminal, máquina §5),
  200 com `DespesaOut`. Não é soft-delete. Só FIN (owner/admin/financeiro).
- **Papéis (ESPEC §9 + Dicionário §4.3):** `gestor` lê tudo, lança e edita despesa (inclui
  parcelada), lê categorias; **não** paga, cancela, estorna, recebe, nem mexe em categorias,
  cronograma ou medição. `orcamentista` só vê orçado × realizado e Curva S. `receber` = FIN, por
  analogia ao pagamento. `campo`, `viewer`, `ai`: sem acesso.
- **Adições fora da ESPEC:** `numero_periodos` opcional (1–520) ao criar cronograma (CA-F01.3);
  `periodicidade` (`semanal`|`mensal`, padrão mensal) no fluxo de caixa, com `de`/`ate`
  obrigatórios e `obra_id` opcional (CA-F13.2); filtros do CSV `status`, `obra_fase_id`,
  `categoria_id`, `de`, `ate` (CA-F14.1); campos de estado vazio na análise
  (`tem_orcamento_aprovado`, `tem_cronograma`, `corrente`, `estourou`, `percentual_consumido` como
  fração, nulo com orçado 0); Curva S em R$ com as séries `planejado_acumulado`,
  `medido_acumulado`, `realizado_acumulado`; aprovar medição devolve
  `{medicao, recebimento | null, aviso | null}` e `vencimento` é opcional (CA-F04.7).
- **Revisão da S-F2, aprovada pelo humano em 2026-11-12 (ciclo 2):** fluxo de caixa com
  `saldo_previsto`/`saldo_realizado` e os acumulados de cada um, em vez de um `saldo` ambíguo
  (US-F13); `RecebimentoOut` com `obra_nome` e `medicao_numero`, `DespesaOut` com
  `fase_descricao` e `categoria_nome` (CA-F10.1); listagem de despesas da obra com `de`/`ate`,
  os mesmos filtros do CSV (CA-F14.1). Nos `*Update`, campo NOT NULL é opcional mas **não
  nulo**; só `documento_id` aceita `null` (= desvincular NF, CA-F07.3).
- **Sem rota para "desfazer recebimento":** a máquina §5 tem a transição, mas o PRD (CA-F10) não a
  pede. Fica fora; desfazer **pagamento** é o `estornar` (CA-F09.3).

---

## E-11 · Decisões da Onda 2/3 (S-F3, S-F4, S-F6) — 2026-11-22

- **Rota nova `GET /obras/{obra_id}/fases`** (humano): lista leve das fases da obra (`id`,
  `codigo`, `descricao`, `ativa`), papéis de leitura de despesa. Implementada na S-F3, em
  `routers/despesas.py` (sem registro novo em `api/v1/__init__.py`). Emenda ao contrato congelado da
  S-F2: o OpenAPI passa a **26 operações em 20 paths**. A tela de lançamento (S-F4) usa esta rota, e
  não a análise da S-F9.
- **Auditoria de `despesa` por gatilho** (humano): `audit_despesa` com a mesma função genérica das
  outras tabelas, criada na própria `0033` (ainda não aplicada fora do banco local). A gravação de
  `audit_log` pelo service sai, para não duplicar.
- **Parcelamento (RN-F08)** (orquestrador): parcela-base truncada (`ROUND_DOWN`) e resíduo na
  última, que nunca fica menor que as demais — 100,00 em 6 = 16,66 × 5 + 16,70. Valor menor que N
  centavos → 422. A prévia da tela (S-F4) usa a mesma regra.
- **`de`/`ate` da listagem e do CSV filtram `vencimento`**, inclusivo nas duas pontas.
- **Pagamento não aceita data futura** (humano): `data_pagamento > hoje` → 422. "Paga" é dinheiro
  que já saiu; agendamento é despesa `prevista` com vencimento.
- **Despesa aponta para fase da MESMA obra no banco** (orquestrador, extensão da E-08):
  `(company_id, obra_id, obra_fase_id) → obra_fase(company_id, obra_id, id)`, com a `UNIQUE` dessa
  tripla em `obra_fase`, na própria `0033`.
- **Decisões do implementador da S-F3, conferidas pelo code-reviewer contra ESPEC §5 e PRD:**
  `PATCH` em despesa paga aceita só `descricao`, `fornecedor_nome` e `documento_id` (o gestor
  edita mas não estorna); transições exatamente as da ESPEC §5, com 422 nomeando a válida;
  categoria desativada barra despesa nova e mantém a já vinculada (CA-F05.4); **fase inativa não
  bloqueia lançamento** na API — `GET /fases` devolve as inativas e a tela filtra; o seed das
  categorias roda nas rotas de categorias.
- **Testes de contrato da fase stub** (orquestrador): `test_financeiro_contrato.py` exigia 501 de
  toda rota. Para rota implementada, o teste troca `get_db` por uma **sessão-sentinela** que levanta
  `_ChegouAoService` no primeiro `execute`: papel autorizado tem de chegar ao service (prova que
  passou por autenticação, papel e validação), sem banco e sem aceitar 500. O 501 continua exigido
  das rotas ainda não implementadas, listadas no teste (`NAO_IMPLEMENTADAS`); cada sprint de backend
  remove as suas da lista e tira o `responses=RESP_501` delas.
- **"Hoje" do negócio é America/Sao_Paulo**, não a data UTC do servidor — senão um pagamento feito
  às 22h seria "futuro".
- A FK em tripla com `obra_id` vale também para `despesa.documento_id → documento(company_id,
  obra_id, id)`, com `ON DELETE SET NULL (documento_id)`.
---

## O que **não** está aqui

Três coisas que pareciam divergência e foram **medidas** como corretas, para ninguém as
"corrigir" de novo:

| Suspeita | Medição |
|---|---|
| Predicado RLS com cast cru vaza em silêncio quando o contexto está vazio | **Não vaza.** Levanta `invalid input syntax for type uuid: ""` — falha fechada e ruidosa. É padrão velho, não furo |
| Policy sem `WITH CHECK` abre a escrita | **Não abre**, numa policy `FOR ALL`: o Postgres usa o `USING` como check. A exigência de escrever o `WITH CHECK` fica por clareza |
| `agent_interaction` tem coluna `feedback` | **Não tem.** A afirmação era minha e estava errada; quem precisar dela precisa de migration |

E os 17 testes vermelhos de `test_photos_sync.py` / `test_documentos_upload.py` não são
divergência: é fidelidade do mock S3 (moto grava zero byte em `PUT` por URL assinada). Ver
`.claude/commands/orquestrador-financeiro.md` §2.
