# Obrax — Especificações Técnicas MVP V1

**Versão:** 1.0 | **Data:** 2026-07-06  
**Alinhamento:** PRD 3.0 · SPRINTS 1.0 · discovery-notes 2026-06-28 · CLAUDE.md  
**Horizonte:** 12 sprints × 2 semanas = 6 meses

---

## ✅ DECISÃO DE ESCOPO CONFIRMADA: PRD V3.0 é a fonte da verdade

| Documento | MVP V1 inclui |
|-----------|--------------|
| discovery-notes.md (2026-06-28) | Módulo 1 (CRM+GED) + Módulo 2 (Orçamentos). Sem IA. |
| PRD V3.0 (2026-06-28) | Módulo 1 + Módulo 2 + Módulo 3 (Agentes IA) |
| **DECISÃO (2026-07-06)** | **PRD V3.0 prevalece. Módulo 3 no MVP V1, restrito a Pro/Enterprise via PostHog feature flag `ia-module-enabled`.** |

O design já inclui todas as telas de IA. Nenhum retrabalho necessário. Usuários Basic veem os itens de IA bloqueados na sidebar (ícone lock + tooltip "Disponível no plano Pro"). A API retorna 403 com `upgrade_url` se tier Basic tentar acessar endpoints do Módulo 3.

---

## 1. Visão Geral do Produto

**Obrax** é um SaaS mini-ERP dark-mode premium para pequenas construtoras e reformadoras (1–30 colaboradores). Resolve controle de custo, gestão documental, transparência com clientes e, no tier Pro, orquestração de compras e consultas via WhatsApp com agentes de IA.

**Produto:** multi-tenant SaaS  
**Público:** Admin/Backoffice (web), Equipe de Campo (mobile-web PWA), Cliente Final (portal web), Fornecedor (magic link — V2)

---

## 2. Stack & Decisões Arquiteturais

### 2.1 Backend

| Camada | Escolha | Versão | Razão |
|--------|---------|--------|-------|
| Linguagem | Python | 3.12 | Ecossistema LLM maduro (LangGraph, LangChain) |
| Framework | FastAPI | 0.115+ | Async nativo, OpenAPI 3.1 automático, Pydantic v2 |
| Process manager | Gunicorn + Uvicorn | latest | 2 workers × 4 threads; escala horizontal |
| Validação | Pydantic v2 | 2.x | `extra='forbid'` whitelist; schemas gerados de models.py |
| Auth hashing | Argon2id | passlib | Mais forte que bcrypt contra GPU attacks |
| ORM | SQLAlchemy Core/ORM | 2.x | Queries parametrizadas obrigatórias; proibido string concat |
| Migrations | Alembic | latest | Forward-only; squawk linter bloqueia DDL perigoso |
| Job runner | Arq | latest | Async-first; scheduler embutido; integra com FastAPI |
| Fila agentes | Redis Streams | — | Consumer groups nativos; backup em `agent_messages` Postgres |
| Orquestrador IA | LangGraph (StateGraph) | latest | Primary: Claude Sonnet; fallback: GPT-4o |
| Storage | Supabase Storage | — | URLs assinadas; RLS sobre buckets; region sa-east-1 |
| PDF | Puppeteer sidecar | — | Template HTML/CSS; pool 3 Chrome headless; target <5s/500 itens |
| Observability | structlog + Prometheus + Sentry + Grafana | — | JSON logs → Loki; spans OTel → Grafana Tempo |

### 2.2 Frontend

| Camada | Escolha | Versão | Razão |
|--------|---------|--------|-------|
| Framework | Next.js App Router | 15.x | RSC + streaming; Server Components default |
| UI runtime | React | 19.x | useOptimistic, useFormStatus, Actions |
| Linguagem | TypeScript strict | 5.6+ | Zero any; tipos TS gerados via openapi-typescript — não editar à mão |
| Estilos | Tailwind v4 | 4.x | CSS-first config; tokens OKLCH |
| Componentes | shadcn/ui + Radix | latest | Copy-paste ownership; A11y WCAG 2.1 AA nativo |
| Server state | TanStack Query v5 | 5.x | Cache + retry + mutations otimistas |
| Client state | Zustand | 4.x | Stores leves (filtros, drawers, toasts) |
| Forms | React Hook Form + Zod | 7/3 | Validação isomórfica client/server |
| Tabelas | TanStack Table v8 | 8.x | Headless; virtualization para 10k+ linhas |
| Realtime | @supabase/supabase-js | 2.x | Channels para tickets e sync de fotos |
| Offline | Dexie v4 | 4.x | IndexedDB wrapper tipado; fila de fotos |
| PWA | @serwist/next | 9.x | Service worker; manifest; precache app-shell |
| Testes unit | Vitest + RTL | latest | ESM; rápido |
| Testes E2E | Playwright | latest | Cross-browser; mobile emulation |
| Mock API | MSW v2 | 2.x | Service worker para dev/testes |
| Observability | Sentry + PostHog | latest | Erros + product analytics; masking PII |

### 2.3 Database & Infra

| Item | Decisão |
|------|---------|
| Engine | PostgreSQL 16 (Supabase managed, sa-east-1) |
| Pooling | PgBouncer transaction mode :6543 |
| Cache | Redis (Upstash serverless ou Fly.io Redis) |
| Hosting API | Fly.io region GRU; autoscale CPU > 70% |
| Hosting Frontend | Vercel (preview deploy por PR) |
| CI/CD | GitHub Actions (lint → typecheck → pytest → build → staging → prod) |
| Secrets | Doppler ou Infisical (rotação JWT a cada 90 dias) |
| Feature flags | PostHog — flag `ia-module-enabled` (Pro/Enterprise), `campo-ocorrencias-enabled` (rollout gradual S8) |

---

## 3. Arquitetura Multi-tenant

**Padrão:** Shared schema + defesa em duas camadas.

**Camada 1 — Middleware FastAPI:**
```python
# TenantMiddleware — executado em cada request
SET LOCAL app.company_id = '<uuid_do_jwt>'
```

**Camada 2 — PostgreSQL RLS:**
```sql
CREATE POLICY tenant_isolation ON obras
  USING (company_id = current_setting('app.company_id', true)::uuid)
  WITH CHECK (company_id = current_setting('app.company_id', true)::uuid);
```

Toda tabela do domínio tem `company_id UUID NOT NULL` indexado. Sem `company_id` explícito no Repository → raise imediato. Testes obrigatórios no CI: cross-tenant SELECT retorna 0 linhas ou 403.

---

## 4. Autenticação & Autorização

### Fluxos

| Fluxo | Mecanismo | TTL |
|-------|-----------|-----|
| Login admin/campo | Argon2id + JWT access (HS256) + refresh httpOnly cookie | 15 min / 30 dias |
| Magic link (portal/aprovação) | JWT separado, claim `purpose`, single-use via `consumed_tokens(jti)` | 30 min |
| Convite de usuário (US-19) | Token opaco 32 bytes URL-safe, SHA-256 armazenado, constant-time compare | 7 dias |
| Sessão cliente portal | Magic link renova; expire 7 dias inatividade | — |

### Roles

`owner` · `admin` · `gestor` · `orcamentista` · `financeiro` · `viewer` · `campo` · `ai` (agentes WhatsApp)

Decorator `@require_perms("budget.write")` em cada endpoint. Revalidação no nível de objeto no service (ex: campo só vê suas obras).

### JWT Claims
```json
{ "sub": "user_uuid", "company_id": "uuid", "role": "admin", "perms": ["budget.write"], "exp": 1234, "jti": "uuid" }
```

---

## 5. Módulos — Guias de Implementação

### 5.1 Módulo 1: Gestão (Sprints 1–4)

**Entidades:** companies, users, user_company_role, clientes, obras, obra_membro, documento, tickets, ticket_mensagens

**Regras críticas:**
- Validação CPF/CNPJ: CHECK constraint + UDF `fn_validate_documento` no Postgres. Duplicidade por documento dentro da mesma empresa → 409 Conflict.
- Soft delete em todas as entidades (coluna `deleted_at`). Hard delete apenas por LGPD (US-21).
- `audit_log` obrigatório em: criação/remoção usuário, alteração visibilidade documento, aprovação orçamento, export LGPD, reversão de ação de agente.
- GED: upload direto ao Supabase Storage via presigned PUT (TTL 15 min). Hash SHA-256 validado no `POST /documentos/confirm`. Dedup por hash dentro da mesma obra.
- Visibilidade documento (US-06): toggle `visivel_cliente` com bulk action; auditoria registra `actor_id` + timestamp. Cache de visibilidade: CDN invalida em <60s.
- Tickets realtime: Supabase channel `obra:{obra_id}:tickets`. Mensagem INSERT dispara evento; frontend aplica via `setQueryData`. Latência alvo <500ms.

**Estrutura de pastas:**
```
app/modules/gestao/
  routers/     — clientes.py, obras.py, documentos.py, tickets.py, usuarios.py
  services/    — crud.py, visibility.py, audit.py
  schemas/     — pydantic models (fonte da verdade)
  models/      — SQLAlchemy ORM
```

### 5.2 Módulo 2: Orçamentos (Sprints 5–6)

**Entidades:** orcamento, orcamento_versao, orcamento_item, insumo (seed SINAPI 10k itens)

**Hierarquia EAP:** Adjacency list + materialized path (columns: `parent_id`, `path`, `depth`). 3 níveis: Fase → Serviço → Insumo/MO.

**Motor de cálculo (`BudgetCalculator`):**
```
Entrada: batch de edições (POST /itens/bulk)
Passo 1: custo_total = qtd × custo_unit  [Decimal(18,6)]
Passo 2: effective_markup = item.override ?? fase.override ?? global
         subtotal_com_markup = custo_total × (1 + markup)
Passo 3: + taxa_administracao aplicada no subtotal da fase/total
Passo 4: agregar bottom-up (insumo → serviço → fase → total)
Transação: SELECT FOR UPDATE na versão → persist → retorna snapshot
```

**Regras críticas:**
- `Decimal` Python + `NUMERIC(18,6)` Postgres. **Proibido `float` em qualquer cálculo financeiro.**
- Orçamento aprovado (`is_locked=true`): trigger Postgres bloqueia UPDATE/DELETE em `orcamento_item`.
- Versionamento: clonar versão é operação atômica; nova versão herda itens da anterior + `numero = anterior + 1`.
- Curva ABC: computada em memória pós-recalculo; classificação A/B/C por percentual acumulado (80/15/5); cacheada em JSON da versão.
- PDF: job Arq na fila `pdf.generate`; Puppeteer sidecar; URL assinada TTL 1h; target <5s para 500 itens.
- Importação XLSX (US-13): template disponível para download; validação linha por linha; erros retornados como array de `{linha, campo, mensagem}`; import até 5000 linhas.

**Estrutura de pastas:**
```
app/modules/orcamento/
  routers/     — orcamentos.py, itens.py, pdf.py
  services/    — budget_calculator.py, versioning.py, curva_abc.py, pdf_job.py
  importers/   — xlsx_importer.py
  schemas/     — pydantic models
```

### 5.3 Módulo 3: Agentes IA (Sprint 10 — tier Pro/Enterprise)

**Feature flag:** PostHog flag `ia-module-enabled`, targeting rule `company_tier IN ('pro', 'enterprise')`. Criado no Sprint 1 junto com o setup inicial.

**Frontend (S1):**
```tsx
// wrapper em todos os itens de IA na sidebar
<FeatureFlag flag="ia-module-enabled" fallback={<NavItemLocked label="Assistente IA" tooltip="Disponível no plano Pro" />}>
  <NavItem href="/ia/assistente" label="Assistente IA" />
</FeatureFlag>
```
Rotas `/ia/*` → redirect para `/upgrade` se flag desabilitada.

**Backend (S10):**
```python
@require_tier('pro', 'enterprise')  # decorator nos endpoints /agentes/* e /webhook/uazap
```
Resposta 403: `{"type": "tier_required", "required_tier": "pro", "upgrade_url": "/upgrade"}`

**Pipeline Webhook Uazap:**
```
POST /webhook/uazap
  → Validar HMAC-SHA256 (X-Uazap-Signature); tolerância replay 5 min → 401 se falhar
  → Idempotência: Redis SET "wa:msg:seen:{message_id}" TTL 24h → 200 ack se existe
  → Rate limit: 10 req/min/número (sliding window Redis) → 429 se exceder
  → Resolver tenant: whatsapp_number → user → company_id; não mapeado → resposta template
  → Persistir em agent_messages (status='pending')
  → Enfileirar em Redis Streams "agent.process"
  → Responder 200 ack < 500ms
```

**Grafo LangGraph:**
```
intake → auth → intent_classifier → router → [subagent_orcamento | subagent_compras] → responder → audit_log
```

Nodes como classes Python com `StateGraph`. Tools como schemas Pydantic com function calling. LLM primário: Claude Sonnet. Fallback automático: GPT-4o. Timeout total: 10s (resposta intermediária em 8s se ainda processando).

**Subagente Orçamento (read-only):** tools `get_orcamento_resumo`, `get_status_obra`. Sem escrita no DB.

**Subagente Compras (write):** tools `criar_solicitacao_compra`, `validar_limite_orcamento`. Requer role `ai=solicitador` ou superior. Human-in-the-loop para pedidos > R$5.000.

**Retry:** Arq `retry()` com backoff 30s/60s/120s. Max 3 tentativas. Após esgotar: `status='failed'` + alerta admin + template "Um humano vai te chamar".

**Auditoria (US-22):** tabela `agent_interaction` append-only; campos: timestamp, phone, command, agent, action, result, feedback. Reversão de ação: `POST /agentes/logs/{id}/reverter` cria compensação e registra em audit_log.

**Estrutura de pastas:**
```
app/modules/agentes/
  routers/     — webhook.py, logs.py, permissoes.py
  graph/       — agente.py (StateGraph), nodes.py, tools.py
  services/    — intent.py, responder.py, audit.py
  integrations/— uazap.py, llm.py
```

---

## 6. Contratos de API (Principais)

Convenções globais: UUID v7 (IDs), cursor-based pagination (`?cursor=&limit=50`), ISO 8601 UTC, RFC 7807 Problem Details para erros, `Idempotency-Key` header em POSTs críticos.

### Auth
```
POST /api/v1/auth/login          → {access_token, expires_in} + Set-Cookie refresh
POST /api/v1/auth/refresh        → novo access_token
POST /api/v1/auth/logout         → revoga refresh
GET  /api/v1/auth/magic/{token}  → valida, marca consumed_tokens, redirect /dashboard
POST /api/v1/auth/aceitar-convite→ set password, ativa user
```

### Gestão
```
POST   /api/v1/clientes                        → 201 {id, ...}
GET    /api/v1/clientes?search=&type=PF|PJ&cursor=
PATCH  /api/v1/clientes/{id}
DELETE /api/v1/clientes/{id}                   → soft delete

POST   /api/v1/obras                           → 201 {id, ...}
GET    /api/v1/obras?status=&cliente_id=&cursor=
PATCH  /api/v1/obras/{id}
DELETE /api/v1/obras/{id}

POST   /api/v1/obras/{id}/documentos           → presigned URL se >5MB
PATCH  /api/v1/documentos/{id}                 → {categoria, visivel_cliente}
POST   /api/v1/documentos/bulk-visibilidade    → {ids:[], visivel: bool}

POST   /api/v1/obras/{id}/tickets
POST   /api/v1/tickets/{id}/mensagens
GET    /api/v1/tickets?obra_id=&status=

POST   /api/v1/photos/sync                     → Idempotency-Key obrigatório → presigned PUT URL
POST   /api/v1/photos/{id}/confirm

POST   /api/v1/usuarios/convite                → 201, envia email
POST   /api/v1/auth/aceitar-convite
PUT    /api/v1/templates-email/{slug}
POST   /api/v1/exports                         → job LGPD, link 7 dias
```

### Orçamentos
```
POST   /api/v1/obras/{obra_id}/orcamentos
POST   /api/v1/orcamentos/{id}/versoes         → clona versão atual
GET    /api/v1/orcamentos/{id}/versoes/{v}
POST   /api/v1/orcamentos/versoes/{vid}/fases
POST   /api/v1/orcamentos/versoes/{vid}/itens/bulk  → recalc cascata retorna snapshot
POST   /api/v1/orcamentos/versoes/{vid}/importar-planilha
GET    /api/v1/orcamentos/versoes/{vid}/curva-abc
PUT    /api/v1/orcamentos/versoes/{vid}/precificacao → {markup_global, markup_fase:{}, markup_item:{}, taxa_adm}
POST   /api/v1/orcamentos/versoes/{vid}/pdf    → job Arq, retorna job_id
GET    /api/v1/orcamentos/versoes/comparar?a={v1}&b={v2}
POST   /api/v1/portal/orcamentos/{magic_jti}/decisao → {acao: 'aprovar'|'rejeitar', comentario}
```

### Agentes IA
```
POST   /webhook/uazap                          → 200 ack <500ms (sem /api/v1)
GET    /api/v1/agentes/logs?obra_id=&tipo=&from=&to=
POST   /api/v1/agentes/logs/{id}/reverter
POST   /api/v1/agentes/feedback/{interaction_id} → {correto: bool}
PUT    /api/v1/agentes/permissoes              → mapeia whatsapp → role + limites
```

---

## 7. Schema de Banco (21+ tabelas)

### Enums
```sql
CREATE TYPE user_role AS ENUM ('owner','admin','gestor','orcamentista','financeiro','viewer','campo','ai');
CREATE TYPE company_tier AS ENUM ('starter','pro','enterprise');
CREATE TYPE obra_status AS ENUM ('planejamento','execucao','pausada','concluida','cancelada');
CREATE TYPE orcamento_status AS ENUM ('rascunho','em_revisao','aguardando_aprovacao','aprovado','rejeitado');
CREATE TYPE documento_tipo AS ENUM ('projeto','contrato','nota_fiscal','foto','outro');
CREATE TYPE agent_kind AS ENUM ('orcamento','compras','atendimento');
CREATE TYPE audit_action AS ENUM ('created','updated','deleted','visibility_changed','approved','rejected','exported','reverted');
```

### Tabelas Core
```sql
companies (id UUID PK, cnpj CITEXT UNIQUE, razao_social, tier company_tier, is_active BOOL, created_at)
users (id UUID PK, email CITEXT UNIQUE, password_hash TEXT, nome, phone, created_at, deleted_at)
user_company_role (user_id FK, company_id FK, role user_role, created_at)
clientes (id, company_id, tipo_pessoa CHAR(2), documento CITEXT, nome, telefone, email, created_at, deleted_at)
  UNIQUE (company_id, documento)
obras (id, company_id, cliente_id FK, status obra_status, codigo, nome, data_inicio, data_prevista_fim, 
       data_real_fim, valor_contrato NUMERIC(18,2), created_at, deleted_at)
obra_membro (obra_id FK, user_id FK, papel TEXT, created_at)

insumo (id, company_id NULLABLE [NULL=SINAPI global], codigo CITEXT, descricao, unidade, categoria,
        preco_unitario NUMERIC(12,4), created_at)
  INDEX (company_id, descricao) GIN trigram

orcamento (id, company_id, obra_id FK, versao_atual INT DEFAULT 1, status orcamento_status, created_at)
orcamento_versao (id, orcamento_id FK, numero INT, is_locked BOOL DEFAULT false,
                  custo_direto NUMERIC(18,2), markup_global NUMERIC(5,4), taxa_adm NUMERIC(5,4),
                  preco_venda NUMERIC(18,2), margem NUMERIC(5,4),
                  curva_abc_json JSONB, markup_por_fase_json JSONB,
                  pdf_url TEXT, pdf_gerado_em TIMESTAMPTZ, criado_por FK, created_at)
orcamento_item (id, versao_id FK, parent_id FK SELF, path TEXT, depth SMALLINT,
                tipo CHAR(1) ['F'|'S'|'I'], codigo, descricao, unidade,
                quantidade NUMERIC(10,4), preco_unitario NUMERIC(18,6),
                markup_override NUMERIC(5,4) NULLABLE,
                custo_total NUMERIC(18,2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED,
                subtotal NUMERIC(18,2), sort_order INT)
  INDEX (versao_id, parent_id), (versao_id, path)

documento (id, company_id, obra_id FK, nome, tipo documento_tipo, storage_path TEXT,
           size_bytes BIGINT, sha256 CHAR(64), ocr_text TEXT,
           categoria TEXT, visivel_cliente BOOL DEFAULT false,
           uploaded_by FK users, created_at, deleted_at)
  INDEX (obra_id, categoria), GIN tsvector(nome || ' ' || coalesce(ocr_text,''))
  UNIQUE (obra_id, sha256)

ticket (id, company_id, obra_id FK, titulo, descricao TEXT, status TEXT, created_by FK, created_at)
ticket_mensagem (id, ticket_id FK, author_id FK, content TEXT, attachment_paths TEXT[], created_at)

photo (id, company_id, obra_id FK, client_photo_id UUID UNIQUE, sha256 CHAR(64),
       storage_path TEXT, size_bytes INT, sync_status TEXT, captured_at, synced_at)
  UNIQUE (company_id, client_photo_id)

agent_session (id, company_id, user_id FK, obra_id FK NULLABLE, agent_kind, created_at)
agent_message (id, session_id FK, role TEXT, content TEXT, tokens_in INT, tokens_out INT, created_at)
  PARTITIONED BY RANGE (created_at) [mensal]

agent_interaction (id, company_id, message_id TEXT, phone TEXT, agente agent_kind,
                   command TEXT, intent TEXT, confidence NUMERIC(4,3),
                   action TEXT, result TEXT, feedback BOOL NULLABLE,
                   attempts SMALLINT DEFAULT 0, status TEXT, received_at, processed_at)

consumed_tokens (jti TEXT PK, consumed_at TIMESTAMPTZ, expires_at TIMESTAMPTZ)
  INDEX expires_at [job limpeza diária]

invitations (token_hash CHAR(64) PK, email CITEXT, company_id FK, role user_role,
             expires_at, accepted_at NULLABLE)

email_template (id, company_id FK NULLABLE, slug TEXT, assunto TEXT, corpo TEXT,
                UNIQUE (company_id, slug))

lgpd_request (id, company_id FK, requested_by FK, request_type TEXT, status TEXT,
              payload_path TEXT NULLABLE, created_at, completed_at)

audit_log (id, company_id FK, actor_id FK, action audit_action, entity TEXT, entity_id UUID,
           before_jsonb JSONB, after_jsonb JSONB, ip INET, ua TEXT, created_at)
  PARTITIONED BY RANGE (created_at) [mensal]
  [REVOKE UPDATE, DELETE ON audit_log — append-only por policy]
```

### Índices Críticos
```sql
-- Todos os company_id + status/created_at em tabelas principais
CREATE INDEX ON obras (company_id, status);
CREATE INDEX ON obras (company_id, created_at DESC);
CREATE INDEX ON documento (obra_id, categoria);
CREATE INDEX ON orcamento_item (versao_id, parent_id);
CREATE INDEX ON orcamento_item (versao_id, path);
CREATE INDEX ON documento USING GIN (to_tsvector('portuguese', nome || ' ' || coalesce(ocr_text,'')));
CREATE UNIQUE INDEX ON documento (obra_id, sha256);
CREATE INDEX ON agent_interaction (company_id, received_at DESC);
CREATE UNIQUE INDEX ON photo (company_id, client_photo_id);
```

---

## 8. Inventário de Componentes Frontend

| US | Componentes | Rota | Estados |
|-----|------------|------|---------|
| US-01 Dashboard | KpiCard, ObrasOverview, AlertList, CurvaSChart, FluxoCaixaChart, CurvaABCTable, ContasCard | /dashboard | skeleton, empty, error, realtime |
| US-02/03 Obras | DataTable, ObraForm (RHF+Zod), FilterBar, StatusBadge | /obras | form validation, submission |
| US-04 Detalhe obra | ObraHeader, Tabs (cronograma, equipe, docs, fotos, chamados, orçamentos) | /obras/[id] | realtime Supabase channel |
| US-05 Insumos | ComboBox virtualized, servidor-side debounce 500ms | modal/insumo | 10k items sem lag |
| US-06 Documentos GED | FileDropzone, DocGrid/DocList, VisibilityToggle, BulkActionBar, DocViewer | /obras/[id]/documentos | upload progress, dedup SHA256 |
| US-08/09 Tickets | TicketForm, TicketChat (realtime), AttachmentPreview | /tickets/[id] | thread, attachments |
| US-09 Campo fotos | PhotoCapture, SyncStatusBadge, OfflineQueue | /obra/[id]/foto | IndexedDB, 30s retry |
| US-11/12 Orçamentos | OrcamentoBuilder (fullscreen modal), EapTree, InsumoComboBox, MarkupSlider, BudgetSummary | /orcamentos/[id]/edit | recalc <200ms |
| US-13 Importação | XlsxDropzone, ImportPreview, ErrorList | modal | linha-por-linha erros |
| US-14 Curva ABC | RechartsPareto, ABCTable | aba do builder | recalc real-time |
| US-15 Markup | MarkupPanel (sliders global/fase/item), TaxaAdmInput | aba Precificação | Decimal.js |
| US-16 Versões | VersionList, VersionCompare, NovaRevisaoButton | aba Revisões | imutable snapshot |
| US-17 PDF | PdfButton, PdfProgressModal, PdfViewer | inline na aba | job polling |
| US-18 Portal aprovação | OrcamentoViewer, SignaturePad, AprovarModal | /portal/obra/[token]/orcamento | RSC cache 60s |
| US-19 Convite | InviteForm (email+role+obras), InviteList | /configuracoes | modal |
| US-20 Templates | TemplateEditor (assunto+corpo), TemplateList | /configuracoes | rich text básico |
| US-21 LGPD | ExportDataButton, ExportStatus, DeleteAccountModal | /configuracoes | polling job status |
| US-22 Auditoria IA | AgentAuditTable, InteractionDrawer, ReverterButton, FeedbackButtons | /ia/auditoria | filtros |
| US-23 Permissões IA | PermissoesForm (whatsapp→role+limites), PermissoesList | /configuracoes ou /ia/permissoes | |
| US-24 Assistente IA | AssistantChat (streaming SSE), ContextoBadge, QuickSuggestions | /ia/assistente | mock via MSW |

### Estados Obrigatórios em Todos os Componentes
- **Loading:** Suspense + Skeleton (aparece após 200ms de delay para evitar flash)
- **Empty:** EmptyState com CTA contextual ("Criar primeira obra")
- **Error:** ErrorBoundary com retry button; log em Sentry
- **Offline:** SyncStatusBadge visível globalmente no campo; filas IndexedDB persistem entre sessões

---

## 9. Design System (tokens)

```css
/* Backgrounds */
--bg-base:    #1a1c24;  /* body */
--bg-card:    #242833;  /* cards, modais */
--bg-sidebar: #1e2130;  /* sidebar */

/* Brand */
--coral:    #ff6b6b;  /* CTAs, crítico, alertas */
--violet:   #845ef7;  /* previsto, variante primária */
--teal:     #38d9a9;  /* realizado, sucesso */

/* Text */
--text-primary:   #e8eaf0;
--text-secondary: #8c92a4;
--text-muted:     #5b6072;

/* Fonts */
font-family: 'Manrope', sans-serif;          /* corpo, labels */
font-family: 'JetBrains Mono', monospace;   /* valores financeiros, códigos */

/* Design tokens disponíveis via classe CSS */
.obx-nav    /* item de navegação */
.obx-card   /* card container */
.obx-kpi    /* KPI card */
.obx-row    /* linha de tabela */
.obx-edit   /* modo edição inline */
.obx-cta    /* botão primário coral */
.obx-ghost  /* botão ghost */
```

---

## 10. Segurança & Performance

### Segurança Frontend
| Aspecto | Implementação |
|---------|--------------|
| XSS | DOMPurify em HTML renderizado (chat IA, notas ricas) |
| CSRF | SameSite=Strict + double-submit cookie |
| CSP | `default-src 'self'; img-src 'self' data: blob: <storage>; connect-src 'self' <api> <supabase>` |
| JWT | Cookie HttpOnly — **nunca localStorage** |
| PII em logs | Sentry `beforeSend` redact CPF, telefone, email |

### Performance Targets
| Métrica | Target | Como medir |
|---------|--------|-----------|
| LCP | <2.5s | RSC + streaming, next/image, next/font local |
| INP | <200ms | useTransition em filtros |
| CLS | <0.1 | reservar altura de imagens |
| JS gzip admin | <200KB | webpack-budget CI gate |
| JS gzip field | <120KB | code-split Chart/Gantt/SignaturePad |
| Recalc orçamento | <300ms (1000 itens) | benchmark obrigatório pré-deploy |
| API P95 | <1.5s | Prometheus http_request_duration |
| Agent P95 | <5s | Prometheus agent_response_duration |
| Upload dedup | 409 <100ms | Redis hit |
| PDF (500 itens) | <5s | job Arq benchmark |
| Realtime ticket | <500ms | Supabase channel latency |

---

## 11. Qualidade & CLAUDE.md Preferences

Estas specs seguem as diretrizes do CLAUDE.md do projeto:

**Correção > Velocidade:** todo critério de aceite por sprint é verificável; sem tarefas concluídas com testes vermelhos.

**Premissas declaradas (incluindo decisões confirmadas):**
- PRD V3.0 é fonte da verdade para escopo MVP V1 — inclui Módulo 3 (IA). Discovery-notes tem escopo menor mas foi supersedido. **Decisão confirmada em 2026-07-06.**
- Módulo 3 restrito a Pro/Enterprise via PostHog flag `ia-module-enabled`. Basic vê itens bloqueados, API retorna 403. **Não implementar acesso duplo — usar o flag.**
- Tipos TS são gerados via `openapi-typescript` a partir de `backend/server/models.py` — **não editar à mão**
- Migrations são forward-only; `langgraph.json` e schemas do grafo LangGraph não podem ser alterados após deploy sem migration de estado
- `Decimal` Python + `NUMERIC(18,6)` Postgres em todos cálculos financeiros — **`float` proibido em qualquer cálculo de orçamento**
- Sidebar itens "Compras" e "Financeiro" ficam visualmente desabilitados no MVP (Módulos 4 e 6 são V2); não criar telas para eles

**Simplicidade:** sem abstrações para uso único; factories/interfaces só com múltiplas implementações; refatorar para <50 linhas quando possível.

**Mudanças cirúrgicas:** editar apenas o necessário; não "melhorar" código adjacente; imports órfãos removidos só se a mudança os criou.

**Definição de concluído:** `make test && make lint` verde antes de reportar tarefa concluída.

### Cobertura de testes obrigatória
```
Módulos críticos (auth, calculo, agentes): mínimo 70%
Endpoints sensíveis (permissão, visibilidade, cross-tenant): 100%
E2E Playwright: 12 fluxos (login, obra CRUD, builder orçamento, campo upload, portal aprovação, agente chat)
```

---

## 12. Critérios de Saída por Sprint (Resumo)

| Sprint | Entrega | Critérios chave |
|--------|---------|----------------|
| S1 | Setup + Auth | Login funciona, magic link single-use, CI verde, staging deployável |
| S2 | Obras CRUD | DataTable + filtros, drawer criar/editar, TanStack Query integrado |
| S3 | GED + Equipes | Upload presigned URL, visibilidade toggle + bulk, busca fulltext <1s |
| S4 | Tickets + Dashboard | Chat realtime <500ms, KPIs do dashboard, notif e-mail |
| S5 | Orçamentos EAP | Builder 3 abas, drag-drop, recalc <300ms/1000 itens, import XLSX |
| S6 | BDI + PDF | Curva ABC, markup 3 níveis, PDF <5s/500 itens, job queue Arq |
| S7 | Field Setup | PWA instalável, Dexie funcional, worker sync 30s, offline indicator |
| S8 | Fotos + Ocorrências | Presigned PUT, dedup SHA256+UUID, realtime <1s, retry backoff |
| S9 | Portal Cliente | Magic link portal, aprovação orçamento, LGPD export ZIP 7d |
| S10 | Agentes IA | Webhook HMAC, fila Redis, LangGraph routing, audit + permissões |
| S11 | Hardening | A11y 0 críticos, E2E 12 fluxos, bundle <200KB admin, logs Loki |
| S12 | Beta + GA | 3+ clientes beta, 0 bloqueadores, deploy blue-green zero-downtime |

---

## 13. Tiers & Monetização

| Feature | Basic (R$99/mês) | Pro (R$299+R$49/seat) | Enterprise (custom) |
|---------|-----------------|----------------------|---------------------|
| Obras | máx 5 | ilimitado | ilimitado + multi-empresa |
| Usuários | 2 | ilimitado | ilimitado + SSO SAML |
| Módulos 1+2 | ✅ | ✅ | ✅ |
| Módulo 3 IA | ❌ | ✅ (Orçamento + Compras) | ✅ + prompt customizado |
| Templates e-mail | padrão | customizável | customizável |
| Documentos | 500/empresa | ilimitado | ilimitado |
| Storage | 5GB | 100GB | ilimitado |
| SLA uptime | — | 99.5% | 99.9% |

**Regra de limite:** ao atingir 5 obras no Basic, sistema bloqueia criação + exibe modal de upgrade. Feature flags (PostHog) controlam acesso ao Módulo 3.

---

## 14. Observabilidade (Métricas Críticas)

```
http_request_duration_seconds   P95 < 1.5s → alerta se > 2s por 5 min
budget_recalc_duration_seconds  P95 < 300ms
agent_response_duration_seconds P95 < 5s → alerta se degraded
agent_interpretation_correct    >= 90% → métrica feedback loop
agent_queue_depth               alerta se > 1000 por 5 min
uazap_up / llm_up / storage_up  alerta se down > 5 min
db_pool_in_use                  alerta se > 80%
erro_5xx_ratio                  alerta se > 1% por 5 min
llm_custo_diario                alerta se > 80% do budget do tier
```

---

## 15. LGPD (US-21)

| Obrigação | Implementação |
|-----------|--------------|
| Export de dados | Job ZIP: clientes.json, obras.json, orcamentos.json, documentos.csv, tickets.json; link single-use TTL 7 dias |
| Exclusão (right to be forgotten) | Soft delete 30 dias → hard delete + tombstone em audit_log |
| Retenção | invoices/contratos 5 anos (CTN); audit_log 2 anos online + 5 anos cold; agent_messages 90 dias |
| Masking em dev | pg_dump com redação de PII (CPF, CNPJ, email, telefone) |
| Região | Supabase sa-east-1 (São Paulo) |

---

*Documento gerado com base em: PRD V3.0, SPRINTS V1.0, discovery-notes 2026-06-28, CLAUDE.md.*
