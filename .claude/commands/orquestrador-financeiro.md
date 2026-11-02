---
description: Executa o plano dos Módulos 5 e 6 (planejamento físico-financeiro e financeiro) despachando as sprints de docs/modulo-financeiro/SPRINTS.md
---

# Orquestrador — Módulos 5 e 6

Você executa `docs/modulo-financeiro/SPRINTS.md`. Você **não implementa nada**: despacha, verifica
o portão, registra status. Implementação é dos agentes.

## 1. Fonte de verdade

| O quê | Onde | Quem edita |
|---|---|---|
| Escopo, critérios, arquivos, dependências | `docs/modulo-financeiro/SPRINTS.md` | **só você** |
| Requisito de produto, `US-F*`, `CA-F*`, `RN-F*` | `docs/modulo-financeiro/PRD.md` | ninguém sem aprovação humana |
| Decisão técnica, contratos, isolamento | `docs/modulo-financeiro/ESPEC.md` | ninguém sem aprovação humana |
| Schema, constraints, índices, RLS | `docs/modulo-financeiro/DICIONARIO-DE-DADOS.md` | ninguém sem aprovação humana |

Os campos `Status`, `Ciclos` e `Revisores OK` do `SPRINTS.md` são **seus**. Agente que escreve
status produz duas versões da verdade, e na retomada você não sabe qual vale.

Agente que conclui que o PRD, a ESPEC ou o Dicionário está errado **reporta a você e para**. Você
sobe para o humano. Não reescreva requisito para fazer uma sprint fechar — foi assim que a fórmula
de faturamento da RN-F06 quase entrou liberando 100% do contrato com 20% da obra executada.

## 2. Pare antes de começar se

Verifique nesta ordem, **antes do primeiro despacho**:

- [ ] Os quatro documentos de `docs/modulo-financeiro/` existem e abrem.
- [ ] **Todo agente citado em `Agente:` existe em `.claude/agents/`.** Nome inexistente faz a
      sprint morrer em silêncio. Hoje existem: `ai-engineer`, `backend-developer`, `code-reviewer`,
      `devops-engineer`, `fastapi-developer`, `nextjs-developer`, `postgres-dba`,
      `revisor-isolamento`. Confira rodando `ls .claude/agents/`, não de memória.
- [ ] Baseline conferida na `main` **antes** de você mexer em qualquer coisa — ver a medição
      abaixo. Baseline vermelha faz você atribuir a uma sprint uma falha que já existia.
- [ ] Nenhuma sprint com `Status: em andamento` de uma execução anterior. Se houver, leia `Ciclos`
      e `Revisores OK` e retome dali — não reinicie, senão o teto de três ciclos vira ilimitado
      através de reinícios.

### A baseline da `main` não é verde — e você precisa saber *onde*

Medido em 2026-11-02, na `main` em `89593a5`, com Postgres 16 e as migrations aplicadas até a
`0031`:

| Portão | Resultado medido |
|---|---|
| `make migrate` | **verde** — `0001` → `0031` sem erro |
| `make lint` | **verde** — ruff, `ruff format --check` (215 arquivos), mypy (124 arquivos, zero issue) |
| `make test` | **318 passaram · 10 falharam · 7 erros** |

**Os 17 vermelhos estão todos em `tests/test_photos_sync.py` e `tests/test_documentos_upload.py`,
e não são defeito do repositório.** São o mock S3 (moto): num `PUT` por URL assinada ele grava
**zero byte**, enquanto `boto3.put_object` grava o conteúdo certo — medido lado a lado. Os erros
aparecem como `botocore.exceptions.*` e `urllib.error.URLError`.

Consequências para você, as duas que importam:

1. **Não trate esse conjunto como regressão de sprint nenhuma.** Nenhuma sprint dos Módulos 5 e 6
   toca esses arquivos.
2. **Não deixe ninguém "consertar" esses testes.** A correção tentadora é afrouxar a asserção ou
   `skip`, e isso cai na reprovação automática §5.1 — remoção de sinal, não correção.

Antes do primeiro despacho, rode `make test` e confira que o vermelho é **exatamente** esse
conjunto. Vermelho em qualquer outro arquivo é problema novo: pare e suba para o humano.

Um detalhe de ambiente que custa meia hora: `app_user` e `app_admin` são roles **do cluster**, não
do banco. A migration `0001` só os cria `IF NOT EXISTS`, então um cluster que já os tenha com outra
senha faz **toda** a suíte de RLS falhar com `password authentication failed` — 213 falhas e 44
erros que não têm nada a ver com o código. Se vir isso, acerte as senhas
(`app_user_dev_only` / `app_admin_dev_only`, fixas na `0001`) em vez de investigar o schema.

### Dois bloqueios já medidos neste repositório — resolva antes, não durante

**(a) `docs/CLAUDE.md` proíbe o que este plano constrói.** A seção *O que NÃO Tocar* diz:

> Sidebar items "Compras" e "Financeiro" — deixar como `disabled` no MVP V1. Não criar rotas ou
> telas para eles.

E `frontend/components/shared/Sidebar.tsx:38` está exatamente assim. As sprints S-F4, S-F6, S-F8 e
S-F10 criam essas telas e a S-F11 habilita o item. **Contradição direta.** Um agente que leia o
`CLAUDE.md` como instrução vigente recusa o trabalho; um revisor que o leia reprova o trabalho
feito. Registrado em [`docs/modulo-financeiro/ERRATA.md`](../../docs/modulo-financeiro/ERRATA.md) como
**E-01**, com as duas saídas possíveis. Suba para o humano e peça a decisão. **Não despache a
Onda 3 antes disso.**

**(b) Comandos de portão que não existem.** O `docs/CLAUDE.md` manda rodar `make gen-types` e
`make build`; o `Makefile` não tem esses alvos — e diz num comentário que eles "chegam com as
tarefas de frontend/DevOps das próximas sprints". `make check-contract` também não existe (foi
escrito em 2026-08-28 e nunca mergeado). `make test` e `make lint` cobrem **só o backend**.

Portão real, verificado alvo por alvo:

```bash
make test && make lint                       # backend: pytest, ruff, ruff format --check, mypy app
cd frontend && pnpm lint                     # existe
cd frontend && pnpm exec tsc --noEmit        # existe via pnpm exec
cd frontend && pnpm build:budget             # existe
cd frontend && pnpm test:e2e                 # existe (playwright)
```

Os quatro alvos de frontend rodam **direto**, não por `make`. Não bloqueie sprint por
`make check-contract`: trate o critério correspondente da S-F2 como verificação manual contra o
OpenAPI, e registre que o alvo não existe. Registrado como **E-02** na
[ERRATA](../../docs/modulo-financeiro/ERRATA.md).

## 3. Despacho

Percorra as ondas na ordem do `SPRINTS.md` §"Ondas e caminho crítico". Dentro de uma onda,
despache **em paralelo** tudo que o campo `Paralela com:` autoriza, numa única leva.

Para cada sprint, entregue ao agente, integralmente e sem resumir:

1. o `Escopo` e o `Fora de escopo`, literais;
2. a lista de `Arquivos` — com a regra: **só edite o que está listado; precisando de algo fora,
   reporte em vez de editar**. Arquivo fora da lista pertence a outra sprint;
3. todos os `Critérios de aceite`;
4. o `Slot de migration`, quando houver;
5. os links para `ESPEC.md` e `DICIONARIO-DE-DADOS.md` nas seções que a sprint cita.

**Escreva `Status: em andamento` no `SPRINTS.md` antes de despachar.** Sprint marcada como
pendente com trabalho no disco é indistinguível de uma nunca iniciada, e a retomada refaz tudo.

### Roteamento por conteúdo, não por prefixo

O campo `Agente:` é o dono padrão da sprint. O despacho de cada task olha **o que ela faz**:

| A task faz | Vai para |
|---|---|
| migration, DDL, índice, policy, `GRANT`, consulta ao catálogo | `postgres-dba` |
| schema Pydantic, router, `response_model`, dependência de injeção, OpenAPI | `fastapi-developer` |
| service, regra de negócio, cálculo, repository, teste de backend | `backend-developer` |
| página, componente, hook, E2E de frontend, a11y, bundle | `nextjs-developer` |
| CI, `Makefile`, docker, segredo | `devops-engineer` |
| isolamento, RLS, `float` em dinheiro, troca de credencial | `revisor-isolamento` |
| qualidade geral e débito técnico, **depois** do portão | `code-reviewer` |

Task com prefixo `BE-` que na verdade cria migration vai para `postgres-dba`.

**Os sete agentes herdados são genéricos** — nenhum conhece este projeto. O `postgres-dba` é de
performance e replicação, não de RLS; o `backend-developer` fala de Node e Go. Por isso o contexto
que você entrega não é opcional: é o que substitui o conhecimento que o agente não tem. O
`revisor-isolamento` é o único específico, e existe porque revisor genérico não sabe que o pecado
fatal aqui é trocar de credencial quando a policy bloqueia.

## 4. Portão, revisão e ciclos

Portão de sprint é a suíte, não a opinião de ninguém:

```
[ ] implementação concluída
[ ] make test && make lint verdes
[ ] gates de frontend verdes, quando a sprint toca frontend
[ ] todos os critérios de aceite atendidos, um por um
[ ] revisão aprovada
```

`code-reviewer` roda **depois** do portão, para qualidade e débito — não no lugar dele.

Sprint com `Revisor de segurança: sim` (S-F1, S-F3, S-F7, S-F11) **não fecha** sem aprovação do
`revisor-isolamento`, que precisa ter **rodado** as consultas, não lido o diff. Registre cada
aprovação em `Revisores OK:` no momento em que acontece, não no fim.

Atenção ao campo: `Revisor de segurança` **não é** o caminho crítico. A S-F2 está no caminho
crítico e não pede revisor; a S-F3 pede revisor e não está no caminho crítico.

**Teto de 3 ciclos de correção por sprint.** Ao estourar: `Status: bloqueada`, com o motivo. As
paralelas seguem; a onda fica aberta; a sprint volta para replanejamento, **não** para um quarto
ciclo. Suba para o humano.

## 5. Reprovação automática — não gastam ciclo, param a sprint

1. **Teste enfraquecido para passar.** Asserção alterada, `skip` adicionado, tolerância ampliada,
   mock no que estava sob teste. Não é correção, é remoção do sinal. Se isso consumisse ciclo, o
   agente aprenderia que enfraquecer é uma saída.
2. **Troca para `app_admin`/BYPASSRLS para contornar policy.** Erro de policy se corrige na policy.
3. **`float` em cálculo financeiro**, ou `toFixed()` sobre `Number` (RNF-F03, RN-F10).
4. **Edição de arquivo fora da lista `Arquivos`** da sprint.
5. **Edição de migration já aplicada.** Forward-only: crie uma nova.
6. **Dependência nova em `frontend/package.json`.** O arquivo não está na lista de nenhuma sprint,
   de propósito: gráficos são SVG inline. Se a sprint concluir que precisa, **reporte**.
7. **Requisito reescrito** no PRD, ESPEC ou Dicionário por um agente.

## 6. Gate humano — pare e pergunte

Não presuma em nenhum destes. A tendência natural é presumir; por isso está escrito.

- A contradição do `CLAUDE.md` sobre a sidebar (§2a), antes da Onda 3.
- Habilitar o item da sidebar na S-F11, que é o que abre o módulo ao usuário.
- Qualquer coisa que toque `audit_log`, `consumed_tokens`, `langgraph.json` ou
  `frontend/lib/api.d.ts` (ver `docs/CLAUDE.md` > *O que NÃO Tocar*).
- Os quatro pré-requisitos do `SPRINTS.md` §"Pré-requisitos fora deste plano" — `require_tier`,
  cadastro de fornecedor, US-16, job runner. Nenhum bloqueia a execução; todos precisam estar
  decididos antes de abrir o módulo para cliente pagante.
- Estouro do teto de ciclos.

## 7. Ao fechar cada sprint

Pergunte, antes de marcar `concluída`: **"que implementação errada passa em todos estes
critérios?"** Se você achar uma, falta critério — reporte em vez de aprovar. Dois casos reais
deste plano: um conjunto só-negativo de isolamento fica verde num schema onde ninguém vê nada, e
gravar `valor_liberado = 0` passa numa leitura distraída do CA-F04.7, que exige **nulo**.

Depois: atualize `Status`, `Ciclos` e `Revisores OK`; commit em Conventional Commits referenciando
a US (`feat(financeiro): lança despesa por fase (US-F06)`); branch a partir de `main`, PR com CI
verde.
