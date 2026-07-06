# CLAUDE.md

**Projeto:** Obrax  
**Descrição:** SaaS mini-ERP dark-mode premium para pequenas construtoras e reformadoras (1–30 colaboradores). Controle de custo, GED, portal do cliente e agentes IA via WhatsApp.  
**Stack:** Next.js 15 + FastAPI + LangGraph · Supabase (Auth/Postgres/Storage) · Redis · Fly.io/Vercel

---

## Diretrizes de Comportamento

Este projeto prioriza a **correção sobre a velocidade**. Ao interagir com o código, siga rigorosamente as diretrizes abaixo. Para tarefas triviais, use o bom senso.

### 1. Pense Antes de Codificar

Não assuma. Não esconda incertezas. Exponha tradeoffs.

- **Premissas:** Declare explicitamente. Prossiga com a interpretação mais razoável e registre a premissa — não pare por micro-dúvidas.
- **Quando parar e perguntar:** Só interrompa quando a decisão for **irreversível, custosa, ou alterar interface pública / schema / contrato de API**. Para o resto, escolha a opção mais simples, declare a premissa e siga.
- **Interpretações:** Se houver múltiplas abordagens de peso semelhante, apresente-as em vez de decidir silenciosamente.
- **Claridade:** Se o requisito for ambíguo _e_ a escolha errada for cara de reverter, pare e nomeie exatamente o que causa confusão. _Ex: "endpoint deve paginar? o comportamento muda o schema de resposta"._

### 2. Simplicidade Primeiro

Implemente o mínimo necessário para resolver o problema.

- **Escopo:** Não adicione funcionalidades, abstrações para uso único, flexibilidade extra ou "configurabilidade" não solicitada. _Ex: não crie interface/factory para algo com uma única implementação._
- **Robustez:** Evite tratamento de erro para cenários impossíveis. _Ex: não valide `None` num valor que o tipo já garante existir._
- **Refatoração:** Se o código puder ser reduzido (ex: de 200 para 50 linhas), reescreva-o.
- **Teste de Senioridade:** Pergunte-se: "Um engenheiro sênior consideraria isso sobre-engenheirado?". Se sim, simplifique.

### 3. Mudanças Cirúrgicas

Altere apenas o necessário. Limpe apenas a bagunça que você criou.

- **Edição:** Não "melhore" código adjacente, comentários ou formatação. Não refatore o que não está quebrado.
- **Estilo:** Siga o estilo existente, mesmo que não seja a sua preferência.
- **Código Morto:** Se encontrar código morto não relacionado, mencione-o, mas não delete.
- **Órfãos:** Remova apenas imports/variáveis/funções que suas alterações tornaram inúteis.
- **Rastreabilidade:** Cada linha alterada deve ter justificativa direta no pedido do usuário.

### 4. Execução Orientada a Objetivos

Defina critérios de sucesso antes de começar. Itere até a verificação.

- **Critérios:** Transforme tarefas vagas em metas verificáveis.
  - Bug: Escrever teste que reproduz → Fazer passar.
  - Validação: Escrever testes para falhas → Fazer passar.
- **Planejamento:** Para tarefas complexas, declare um plano breve antes de codificar.
- **Definição de concluído:** Rode `make test && make lint` antes de declarar a tarefa concluída. Se falhar, corrija **antes** de reportar — não entregue com testes vermelhos.

---

## Decisões de Produto Confirmadas

Estas decisões foram tomadas e **não devem ser revertidas sem alinhamento explícito:**

| Decisão | Detalhe |
|---------|---------|
| **Fonte da verdade** | PRD V3.0 (não o discovery-notes.md). |
| **Escopo MVP V1** | Módulo 1 (Gestão) + Módulo 2 (Orçamentos) + Módulo 3 (IA). |
| **IA restrita por tier** | Módulo 3 apenas para Pro/Enterprise via PostHog flag `ia-module-enabled`. Basic vê itens bloqueados na sidebar; API retorna 403 com `upgrade_url`. |
| **Sidebar items V2** | "Compras" (Módulo 4) e "Financeiro" (Módulo 6) ficam `disabled` com tooltip "Em breve" durante todo MVP V1. Não criar telas para eles. |
| **Precisão financeira** | `Decimal` Python + `NUMERIC(18,6)` Postgres. `float` é proibido em qualquer cálculo de orçamento. |
| **Tipos TS** | Gerados via `openapi-typescript` a partir de `backend/server/models.py`. Nunca editar à mão. |

---

## Stack

Convenções não-óbvias (o resto está em `package.json` / `pyproject.toml`):

### Backend
- **Linguagem:** Python 3.12 + FastAPI + Uvicorn + Gunicorn.
- **Validação:** Pydantic v2 com `extra='forbid'`. Schemas em `backend/server/models.py` são a **fonte da verdade do contrato**.
- **Auth:** Argon2id (passlib). JWT access HS256 (15 min) + refresh httpOnly cookie (30 dias). Magic links JWT single-use via `consumed_tokens(jti)`. Convites via token opaco SHA-256.
- **Multi-tenant:** `TenantMiddleware` executa `SET LOCAL app.company_id` + RLS PostgreSQL em todas as tabelas. Sem `company_id` explícito no Repository → raise imediato.
- **Agents:** LangGraph (`StateGraph`). LLM primário: Claude Sonnet. Fallback automático: GPT-4o. Tools com schemas Pydantic + function calling.
- **Fila:** Redis Streams (`agent.process`) + backup em `agent_messages` Postgres. Worker: Arq (async-first).
- **Cálculo orçamento:** `BudgetCalculator` service. Decimal(18,6). Recalc cascata em memória → transação única `SELECT FOR UPDATE`.
- **Storage:** Supabase Storage (URLs assinadas; nunca armazenar URL). Buckets: `documents-{env}`, `photos-{env}`, `pdfs-{env}`, `exports-{env}`.
- **PDF:** Puppeteer sidecar (container Node.js separado). Job via Arq fila `pdf.generate`.
- **Qualidade:** Ruff (lint + format), mypy strict, pytest. Cobertura mínima 70% nos módulos críticos; 100% em endpoints de permissão e cross-tenant.

### Frontend
- **Framework:** Next.js 15 App Router. Server Components default. `"use client"` apenas onde necessário (hooks, browser APIs).
- **UI:** shadcn/ui + Radix. Design system via Tailwind v4 com tokens OKLCH.
- **Server state:** TanStack Query v5 (cache + mutations otimistas). Client state: Zustand (filtros, drawers, toasts).
- **Forms:** React Hook Form + Zod. Validação isomórfica client/server.
- **Realtime:** Supabase channels para tickets e sync de fotos. `setQueryData` em eventos recebidos.
- **Offline:** Dexie v4 (IndexedDB) + worker de sync 30s. `SyncStatusBadge` global no layout de campo.
- **Feature flags:** PostHog. Componente `<FeatureFlag flag="ia-module-enabled">` envolve todos os itens e rotas do Módulo 3.
- **Precisão:** Decimal.js para exibição de valores financeiros no frontend. Nunca `toFixed()` em valores de orçamento.
- **Qualidade:** Prettier + TypeScript strict. Vitest + RTL (unit). Playwright (E2E 12 fluxos). MSW v2 (mocks). Sentry (erros + PII redact). PostHog (analytics).

### Database
- **Engine:** PostgreSQL 16 via Supabase (region sa-east-1, PgBouncer transaction mode :6543).
- **Migrations:** Alembic, forward-only. Squawk linter bloqueia `ADD COLUMN NOT NULL sem default` e `CREATE INDEX` não-concorrente. `lock_timeout = 3s`.
- **RLS:** habilitada em todas as tabelas do domínio. Tabelas sem RLS ativa = bug bloqueador de PR.
- **Enums:** criados no Postgres (não em Python). Alterar enum em produção exige migration `expand-contract`.
- **Particionamento:** `audit_log` e `agent_message` particionadas por RANGE mensal.

---

## Mapa de Arquitetura

```
backend/
  app/
    core/             — config, security (JWT/Argon2id), db (SQLAlchemy), deps
    modules/
      gestao/         — clientes, obras, fornecedores, GED, tickets, equipes, usuarios
      orcamento/      — EAP, markup (BudgetCalculator), ABC, versoes, PDF job
      agentes/        — webhook uazap, LangGraph (StateGraph), subagentes, auditoria
      portal/         — cliente final, magic links, aprovação
    jobs/             — Arq workers: pdf.generate, export.generate, email.send, cleanup, agent.retry
    integrations/     — uazap.py, llm.py (Claude+GPT4o), storage.py (StorageClient abstração)
    api/v1/           — routers (montados por módulo)
  tests/

frontend/
  app/
    (auth)/           — login/page.tsx, magic/[token]/page.tsx, auth/aceitar-convite/page.tsx
    (admin)/          — dashboard, obras, orcamentos, ia (restrito), tickets, configuracoes
    (field)/          — minhas-obras, obra/[id]/(checklist|foto|ocorrencia), fila
    (portal)/         — obra/[token]/(page|orcamento|tickets|documentos)
    api/              — auth, presign, webhook (route handlers)
  components/
    ui/               — design system (shadcn base + customizações Obrax)
    modules/          — componentes por módulo (ObraForm, EapTree, TicketChat, etc.)
    shared/           — KpiCard, DataTable, FileDropzone, SyncStatusBadge, FeatureFlag
  lib/
    posthog.ts        — feature flags client
    supabase.ts       — client singleton
    decimal.ts        — helpers Decimal.js para formatação BRL
    dexie.ts          — schema IndexedDB (offlineDB)
  state/              — Zustand stores (ui.ts, auth.ts)
```

**Módulos isolados por audiência (route groups):**
- `(admin)` — sidebar fixa, layout desktop, auth JWT obrigatório, role admin/gestor/orcamentista
- `(field)` — bottom nav, layout mobile-first, auth JWT campo, PWA offline
- `(portal)` — sem sidebar admin, auth magic link, RSC cache 60s

---

## Contrato Front ↔ Back

Ponto de maior acoplamento — trate com cuidado.

- **Transporte:** REST JSON sobre HTTPS. Streaming SSE para o chat do Assistente IA (`/api/v1/ia/stream`).
- **Endpoints principais:** ver `obrax-especificacoes-tecnicas.md` seção 6. Base: `/api/v1/`.
- **Fonte da verdade:** schemas Pydantic em `backend/app/modules/*/schemas.py` (re-exportados via `backend/server/models.py`).
- **Ao mudar o contrato:** atualizar `schemas.py` **e** os testes de integração na mesma PR. Os tipos TS são **gerados** via `openapi-typescript` — **rode `make gen-types`, não edite à mão**.
- **Convenções:**
  - IDs: UUID v7 (ordenável)
  - Paginação: cursor-based (`?cursor=&limit=50`, max 100)
  - Timestamps: ISO 8601 UTC
  - Erros: RFC 7807 `{type, title, status, detail, instance, errors[]}`
  - `Idempotency-Key` header obrigatório em: `POST /photos/sync`, `POST /agentes/compras/*`

---

## Setup e Execução

```bash
# 1. Dependências
uv sync                          # backend Python 3.12
pnpm install                     # frontend

# 2. Ambiente
cp .env.example .env             # preencha as chaves (ver abaixo)

# 3. Serviços locais
docker compose up -d             # Postgres, Redis, MinIO (mock Storage)

# 4. Migrations
cd backend && alembic upgrade head

# 5. Rodar
make dev                         # backend + frontend juntos
make dev-backend                 # só FastAPI (uvicorn reload)
make dev-frontend                # só Next.js

# 6. Verificar antes de concluir qualquer tarefa
make test && make lint           # obrigatório — não reportar concluído com falha

# 7. Gerar tipos TS após mudança de schema
make gen-types                   # openapi-typescript → frontend/lib/api.d.ts

# 8. Build produção
make build
```

**Variáveis obrigatórias** (nunca commitar):
```
SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
JWT_SECRET (rotação a cada 90 dias — janela sobreposição 7d)
REDIS_URL
ANTHROPIC_API_KEY (LLM primário)
OPENAI_API_KEY (LLM fallback)
UAZAP_WEBHOOK_SECRET (HMAC)
POSTHOG_API_KEY
SENTRY_DSN
DOPPLER_TOKEN (ou INFISICAL_TOKEN)
```

---

## O que NÃO Tocar

- **Migrations já aplicadas** — nunca edite; crie uma nova migration forward-only.
- **`langgraph.json`** e o schema de estado do grafo LangGraph — mudanças destroem sessões persistidas em produção. Exige migration de estado + deploy coordenado.
- **`frontend/lib/api.d.ts`** — arquivo gerado por `openapi-typescript`. Rode `make gen-types`, não edite à mão.
- **Tabela `audit_log`** — append-only por policy de banco (`REVOKE UPDATE, DELETE`). Nunca tente corrigir registros de auditoria; crie um registro de compensação.
- **Tabela `consumed_tokens`** — nunca delete entradas válidas; o job de limpeza diário cuida de expirados.
- **Segredos e `.env`** — nunca commitar chaves.
- **Sidebar items "Compras" e "Financeiro"** — deixar como `disabled` no MVP V1. Não criar rotas ou telas para eles.
- **Feature flag `ia-module-enabled`** — não remover a verificação em nenhum endpoint do Módulo 3 ou componente de IA sem aprovação explícita.

---

## Convenções

- **Backend:** Ruff (lint + format), mypy strict (sem `Any` implícito), type hints obrigatórios, Pydantic v2, pytest + testcontainers.
- **Frontend:** Prettier + TypeScript strict, validação com Zod, forms via React Hook Form, `Decimal.js` para valores financeiros.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`). Referenciar US no corpo quando aplicável: `feat(orcamento): add xlsx import (US-13)`.
- **Branches:** `feature/US-XX-descricao`, `fix/descricao` a partir de `main`. PRs obrigatórios com review antes de merge.
- **PRs:** CI deve passar (lint + typecheck + tests + E2E staging) antes de aprovação. Deploy automático para staging em merge para `main`. Deploy para prod requer aprovação manual.

---

## Referências

| Documento | Localização | Conteúdo |
|-----------|------------|---------|
| PRD V3.0 | `docs/PRD.md` | Fonte da verdade de produto. 24 USs, RNFs, roadmap, specs técnicas |
| SPRINTS V1.0 | `docs/SPRINTS.md` | 12 sprints × 2 semanas. Tasks B/F/D/O com critérios de aceite |
| Specs Técnicas | `docs/obrax-especificacoes-tecnicas.md` | Stack decisions, schema, inventário de componentes, contratos de API |
| Comparação Design | `docs/obrax-comparacao-frontend-vs-prd.md` | Cobertura do Claude Design vs PRD. Gaps e próximos passos |
| Prompt Frontend | `docs/obrax-frontend-prompt.md` | Prompt completo para Next.js (design tokens, componentes, hooks) |
| Prompt Design Faltante | `docs/obrax-prompt-claude-design-telas-faltantes.md` | 9 entregas para telas ainda não construídas no Claude Design |
