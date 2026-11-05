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
