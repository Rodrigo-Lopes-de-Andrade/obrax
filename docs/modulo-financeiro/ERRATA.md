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
