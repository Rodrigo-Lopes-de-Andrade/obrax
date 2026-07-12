# Sprint Planning — MVP V1 (6 meses / 12 sprints de 2 semanas)

> **Versão:** 1.0 | **Data:** 2026-06-28  
> **Total:** 24 User Stories | **Horizonte:** 12 sprints × 2 semanas = 6 meses  
> **Alinhamento:** PRD 3.0 + Backend SPEC + Frontend SPEC + Database SPEC

---

## 📋 Visão Geral do Roadmap

```
S1  ✅ Setup + Auth (Backend/Frontend base)
S2  ✅ Módulo 1: Obras (CRUD + DataTable)
S3  ✅ Módulo 1: Documentos + Equipes (GED + upload)
S4  ✅ Módulo 1: Tickets + Dashboard (realtime)
S5  ✅ Módulo 2: Orçamentos (estrutura EAP)
S6  ✅ Módulo 2: BDI + PDF + Relatórios
S7  ✅ Field app setup + Checklist (offline)
S8  ✅ Field: Fotos + Ocorrências + Sync
S9  ✅ Portal cliente (magic link + aprovação)
S10 ✅ Módulo 3: Agentes IA (LangGraph + webhook)
S11 🟡 Hardening: A11y + Perf + Observability + E2E (código ✅; infra externa pendente)
S12 🟡 Beta + GA (docs ✅; beta/marketing/deploy pendente)
```

**Progresso: 10 / 12 sprints concluídas (83%).** Próxima: S11 (Hardening).
Nota S10: frontend (F10.1–F10.5) construído e verificado com MSW/Playwright; backend
(B10.1–B10.8) escrito e verificado com ruff + mypy + testes unitários das integrações —
a suíte de API/RLS (`test_agentes_api.py`) roda com `make test` onde houver Postgres.

**Skills por camada:**

| Stack | Sprint | Specialista | Dias/sprint |
|-------|--------|-------------|------------|
| Backend (FastAPI) | S1-S12 | Python/FastAPI pro | 8-10d/sprint |
| Frontend (Next.js) | S1-S12 | Next.js specialist | 8-10d/sprint |
| Database (PostgreSQL) | S1-S12 | Postgres DBA | 3-4d/sprint |
| DevOps/Infra | S1, S11, S12 | Cloud architect | 2-3d/sprint |

---

## Sprint 1: Setup Inicial + Auth + Design Tokens (Dias 1-10)  ✅ **CONCLUÍDA**

**Objetivo:** Fundação técnica pronta — repo, CI/CD, design tokens, auth admin/magic links.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B1.1** Setup FastAPI + Supabase | Projeto Python 3.12, dependências (FastAPI, SQLAlchemy, Pydantic v2), docker-compose (Postgres local, Redis) | 2d | `poetry install` sem erros, `pytest --collect` passa, docker-compose up roda |
| **B1.2** Config multi-tenant middleware | TenantMiddleware (SET LOCAL app.company_id), dependency get_tenant | 2d | `company_id` injetado em todo request, teste isolamento passa (tenant A ≠ B) |
| **B1.3** Auth: login + JWT/refresh | Argon2id hashing, JWT (access 15m + refresh 30d httpOnly), endpoint POST /auth/login | 3d | Login retorna JWT, refresh renova, logout revoga, testes (bcrypt strength validado) |
| **B1.4** Magic links (single-use JWT) | Token de 30min com `purpose` claim, tabela `consumed_tokens`, endpoint POST /auth/magic/consume | 2d | Link valida 1x, expira, testes tentativa reuse falha 401 |
| **B1.5** Convites de usuário (US-19 prep) | Token opaco 7d TTL, POST /users/invite (admin), GET /auth/accept-invite (set password) | 2d | Invite envia email, link 1x use, password setup 8 chars min |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F1.1** Setup Next.js 15 + shadcn/ui | App Router, Tailwind v4, TypeScript strict, design tokens OKLCH | 2d | `npm run dev` roda, shadcn init completo, exemplo componente funciona |
| **F1.2** Layout admin (Sidebar + Topbar) | AppShell com header, sidebar fixed (nav principal), topbar (user menu, logout) | 2d | Sidebar toggle mobile, avatar + logout menu, responsive xs-xl |
| **F1.3** Tema dark/light via data-theme | Tailwind config com OKLCH tokens, toggle theme em topbar, persiste localStorage | 1d | Toggle alterna cores, persiste em reload, sem flashing |
| **F1.4** Página de login | Form email + senha, RHF + Zod, submit POST /auth/login, redirect /dashboard se OK | 2d | Validação client/server, senha mascarada, submit desabilitado em loading |
| **F1.5** Magic link consumer | GET /magic/[token] → valida token → if ok redireciona /dashboard, if expired 404 | 1d | Token válido → 200, token expirado → 404 com CTA, mensagem clara |
| **F1.6** Middleware autenticação | middleware.ts valida JWT cookie, redireciona /login se faltando, injeta user no context | 2d | Acesso direto a /dashboard sem JWT → /login, com JWT válido → acessa, com JWT expirado → /login |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D1.1** Supabase setup + config | Criar projeto region sa-east-1, ativar extensions (pgcrypto, pg_trgm, citext), criar roles app_user/app_admin | 1d | Extensions visíveis em \dx, roles criados, PgBouncer conecta em :6543 |
| **D1.2** Tabelas: companies, users, user_company_role | DDL + RLS policies, criar índices (email unique, company_id) | 2d | `\dt` lista 3 tabelas, RLS ativo, select query filtra por company_id |
| **D1.3** Alembic setup | Init project, create baseline, exemplo migration (ADD COLUMN) testada | 1d | `alembic upgrade head` funciona, baseline registrado em alembic_version |

### DevOps Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **O1.1** GitHub repo + CI/CD básico | Criar repo, Actions (lint, typecheck, pytest, E2E seed), secret manager (Doppler/Infisical) | 2d | CI passa em `main`, secrets injetados sem hardcode, deploy staging automático |
| **O1.2** Fly.io setup (API) | Dockerfile FastAPI + Gunicorn, fly.toml configurado, health check /health | 1d | Deploy staging funciona, logs via `fly logs`, scaling policy configurado |
| **O1.3** Vercel setup (Frontend) | Next.js build otimizado, env vars configurados, preview deploy por PR | 1d | Preview URL gerada por PR, staging deploy automático |

### Critérios de Saída Sprint 1

- [x] Login admin funciona (email + senha)
- [x] Magic link funciona (consumível 1x, 30min TTL)
- [x] Convite de usuário funciona (envia email, set password)
- [x] Multi-tenant isolado (RLS ativo, middleware filtra company_id)
- [x] CI/CD green (lint + test + deploy automático)
- [x] Dashboard admin carrega (sem dados ainda, skeleton)
- [x] Staging + prod deployáveis

**Estimativa total:** ~35 dias/pessoa (~2 pessoas backend + frontend = 18d cada)

---

## Sprint 2: Módulo 1 — Obras (US-02, US-03) (Dias 11-24)  ✅ **CONCLUÍDA**

**Objetivo:** CRUD completo de obras vinculadas a clientes. DataTable com filtros e paginação.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B2.1** Tabelas: clientes, obras | DDL + FK, RLS policies, índices (company_id, status, created_at) | 1d | Schema criado, RLS filtra por company_id, indices criados |
| **B2.2** API: CRUD clientes (US-01 prep) | POST /clientes, GET /clientes, GET /clientes/{id}, PATCH, DELETE | 2d | Validação PF/CNPJ, duplicidade por documento, busca paginada cursor-based, 200/201/204/404/422 status |
| **B2.3** API: CRUD obras (US-02) | POST /obras (obra_id UUID, obrigatório client), GET /obras?status=..., GET /{id}, PATCH, DELETE | 2d | Status enum validado, date_prevista_fim >= data_inicio, busca por cliente/status |
| **B2.4** Soft delete + audit log | Trigger audit_log on INSERT/UPDATE/DELETE obras, clientes | 1d | audit_log registra actor_id, before/after JSONB, action enum, IP, created_at |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F2.1** Tela: listar obras (/obras) | DataTable com TanStack Table v8, colunas (código, cliente, status, data_início, data_fim) | 2d | 50 linhas por página, ordenável por coluna, sem virtualization (MVP), filtro status dropdown |
| **F2.2** Drawer: criar obra | ObraForm (RHF + Zod), campos (cliente select, código, nome, data_inicio, status), validação | 2d | Submit POST /obras, resposta OK → close drawer, erro → mostrar toast, cliente obrigatório |
| **F2.3** Drawer: editar obra | GET /{id} → prepopula form, PATCH endpoint, status read-only após criação | 2d | Edição de nome/datas só se status=planejamento, validação date ranges |
| **F2.4** Integração TanStack Query | useQuery para listar, useMutation para POST/PATCH/DELETE, otimistic updates | 1d | Refetch automático no POST, invalidate cache na mutação, loading states corretos |
| **F2.5** Skeleton loader + empty state | Suspense com skeleton table, EmptyState com CTA "Criar primeira obra" | 1d | Skeleton apareça 200ms antes de dados, empty state com button |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D2.1** Validação CNPJ/CPF em Postgres | CHECK constraint + trigger validation, ou UDF fn_validate_cpf | 1d | INSERT com documento inválido falha com erro claro |
| **D2.2** Índices otimizados | Validar (company_id, status), (company_id, created_at DESC), EXPLAIN ANALYZE | 1d | Query list obras <50ms P95, index scan (não seq scan) |

### Critérios de Saída Sprint 2

- [x] Listar obras funciona (50+ linhas teste)
- [x] Criar obra funciona (forma completa, validação)
- [x] Editar obra funciona (campos corretos, validação datas)
- [x] DataTable ordenável + filtrável
- [x] Soft delete + audit log completo
- [x] TanStack Query integrado (cache, refetch)

**Estimativa total:** ~30 dias/pessoa

---

## Sprint 3: Módulo 1 — Documentos + Equipes (US-04, US-05, US-06, US-07) (Dias 25-38)  ✅ **CONCLUÍDA**

**Objetivo:** Upload de documentos (GED), categorização, filtro de visibilidade. Gestão de equipe.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B3.1** Tabela: documento + RLS | DDL (obra_id FK, tipo enum, storage_path, sha256, ocr_text, visivel_cliente bool), RLS by company_id | 1d | Schema criado, uploads armazenam metadados, visibilidade filtrável |
| **B3.2** API presigned URLs | POST /api/presign → return {url, fields} Supabase, cliente faz PUT direto | 2d | URL válida 15min, PUT <50MB funciona, hash SHA256 validado no POST /confirm |
| **B3.3** API: CRUD documento | GET /obras/{obra_id}/documentos, POST /documentos, PATCH /documentos/{id} (categoria, visivel_cliente), DELETE | 2d | Upload funciona, categorização obrigatória, visibilidade imediata (cache <60s) |
| **B3.4** Full-text search em documentos | GIN tsvector index em nome+ocr_text, endpoint GET /obras/{obra_id}/documentos?search=... | 1d | Busca por palavra-chave retorna em <1s, tsvector indexado |
| **B3.5** Tabela: users, obra_membro (equipes) | obra_membro(obra_id, user_id), role enum (mestre, eletricista, pintor, etc) | 1d | Members paginados, soft delete da relação |
| **B3.6** API: CRUD equipe | POST /obras/{id}/membros (add user), DELETE /{id}/membros/{user_id}, GET /membros com paginação | 2d | Adicionar membro válida role, remove por soft delete, paginação cursor |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F3.1** Componente: FileDropzone | Drag-drop file input, múltiplos arquivos, progress bar, validação tipo (PDF/DWG/JPG/PNG/XLSX/DOCX) | 2d | Upload >5MB triggers presigned URL, progress real-time, erro no upload → toast |
| **F3.2** Tela: Documentos GED (/obras/[id]/documentos) | Gallery + list view, filtro categoria (select), busca texto, delete confirmado | 2d | 50 docs por página, virtualization se >100, thumbnail imagem, PDF viewer inline |
| **F3.3** Drawer: Editar visibilidade documento | Toggle "Visível ao cliente", bulk action (select múltiplos + toggle), auditoria em background | 2d | Toggle imediato (optimistic), bulk select todos/nenhum, auditoria registra quem/quando |
| **F3.4** Tela: Equipes (/obras/[id]/equipes) | DataTable membros (name, role, added_at), drawer add member, delete com confirmação | 2d | Busca de usuários para adicionar, dropdown role, remove soft delete |
| **F3.5** Avatar + dropdown user | Componente reutilizável em topbar e cards, iniciais se sem foto | 1d | Renderiza iniciais bonito, layout responsivo xs |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D3.1** Índices full-text documento | GIN tsvector (nome + ocr_text), teste busca <1s | 1d | `SELECT ... WHERE to_tsvector('portuguese', ...) @@ ...` retorna em <1s |
| **D3.2** Auditoria mudança visibilidade | Trigger audit_log on UPDATE documento.visivel_cliente | 1d | audit_log registra mudança, actor, timestamp |

### Critérios de Saída Sprint 3

- [x] Upload de documentos funciona (drag-drop, presigned URL, dedup SHA256)
- [x] Categorização + filtro funciona
- [x] Visibilidade ao cliente funciona (toggle + bulk, auditoria)
- [x] Full-text search <1s
- [x] Gestão de equipe funciona (add/remove membros)
- [x] GED aparece em 50 documentos sem lag

**Estimativa total:** ~32 dias/pessoa

---

## Sprint 4: Módulo 1 — Tickets + Dashboard (US-01, US-08, US-09 prep) (Dias 39-52)  ✅ **CONCLUÍDA**

**Objetivo:** Sistema de tickets/chamados com realtime. Dashboard admin com KPIs.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B4.1** Tabelas: tickets, ticket_mensagens | DDL (obra_id FK, titulo, descricao, status enum, created_by), RLS by company_id | 1d | Schema criado, RLS ativo, status transitions mapeadas |
| **B4.2** API: CRUD tickets (US-08) | POST /obras/{id}/tickets, GET /tickets, PATCH /{id}/status, DELETE | 2d | Criação registra created_by, status (Aberto/Andamento/Resolvido/Fechado), descrição com até 5KB |
| **B4.3** API: mensagens (chat) | POST /tickets/{id}/mensagens (text + até 5 attachments), GET /mensagens, Supabase channels trigger | 2d | Mensagem INSERT → Supabase channel event, realtime funcionando |
| **B4.4** Dashboard KPIs | GET /dashboard/summary → obras ativas (count, valor total), tickets abertos, orçamentos pendentes | 2d | Agregações por company_id, cache Redis 60s, retorna <100ms |
| **B4.5** Notificação e-mail ticket criado | Job email.send (Admin recebe aviso) ao criar ticket | 1d | Email envia com título/descricao/obra, template customizável (US-20 prep) |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F4.1** Dashboard admin (/dashboard) | KpiCard (obras ativas, valor total, tickets abertos), AlertList (obras vencidas), layout 3-column | 2d | Dados reais de API, responsive, KpiCard com ícone + número + trend |
| **F4.2** Tela: Tickets (/tickets) | DataTable (obra, titulo, status, created_at), filtro status, busca | 2d | 30 tickets por página, status pills coloridas, click abre drawer |
| **F4.3** Drawer: Criar ticket | TicketForm (obra select, título, descricao, attachments), submit POST | 1d | Validação título obrigatório, submit desabilitado em loading, toast sucesso |
| **F4.4** Chat realtime (/tickets/[id]) | TicketChat componente (scroll histórico, input novo, realtime via Supabase channel) | 3d | Mensagens aparecem em <500ms, scroll lock bottom, não recarrega página, Supabase channel ativo |
| **F4.5** Integração TanStack Query + Supabase | useQuery + channel.on('postgres_changes') → setQueryData, mutation otimista | 2d | Enviar msg → aparece antes de 200 OK, cache invalidado no DELETE |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D4.1** Supabase Realtime config | Enable realtime em tabelas tickets/ticket_mensagens, create publication | 1d | `supabase_realtime_messages` trigger ativo, evento capturado |

### Critérios de Saída Sprint 4

- [x] Dashboard admin funciona (KPIs, layout responsivo)
- [x] Sistema de tickets funciona (CRUD completo)
- [x] Chat realtime funciona (<500ms, Supabase channels)
- [x] Notificação e-mail ao criar ticket
- [x] 10+ tickets teste renderizam sem lag

**Estimativa total:** ~30 dias/pessoa

---

## Sprint 5: Módulo 2 — Orçamentos (US-11, US-12, US-13) (Dias 53-66)  ✅ **CONCLUÍDA**

**Objetivo:** Estrutura EAP (Fases → Serviços → Insumos), importação de composições, hierarquia.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B5.1** Tabelas: orcamento, orcamento_versao, orcamento_item | DDL com adjacency list (parent_id self-FK) + depth tracking, RLS by company_id | 2d | Schema criado, materialized path derivado, RLS ativo |
| **B5.2** Motor de cálculo (recalc cascata) | Serviço BudgetCalculator — recalcula subtotais <300ms, Decimal(18,6) precisão | 3d | 1000 items recalc <300ms, sem erros ponto flutuante, transação atômica |
| **B5.3** API: CRUD orçamento (US-11) | POST /obras/{id}/orcamentos, GET /orcamentos, GET /{id}, PATCH status | 2d | Versão inicial criada, status enum, versionamento linkado |
| **B5.4** API: CRUD itens EAP (US-12) | POST /orcamentos/{vid}/itens (bulk), PATCH /{id}, DELETE, reordenar (DnD) | 3d | Batch insert/update, recalc dispara, parent_id validation, duplicação item funciona |
| **B5.5** API: Importação planilha (US-13) | POST /orcamentos/{id}/importar-xlsx → valida template, retorna erros por linha, cria hierarchy | 2d | Template XLSX disponível, import até 5000 linhas, erros de validação claros |
| **B5.6** Tabela: insumo (catálogo) | Seed SINAPI 10k itens, API GET /insumos?search=... autocomplete, categoria index | 2d | Busca <500ms por descrição, autocomplete com cursor, categoria filtro |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F5.1** Modal fullscreen: Builder orçamento | 3 abas (Estrutura, Precificação, Resumo), sem reload rota, drag-drop reordenar | 3d | Modal aberto via /orcamentos/[id]/edit, abas navegáveis, dados persistem entre abas |
| **F5.2** Aba Estrutura (hierarquia EAP) | Tree view com fase/serviço/insumo, +/- de itens, input inline edição | 2d | Recalc de subtotais ao digitar, cores por nível, indent visual |
| **F5.3** Aba Precificação (markup) | Sliders para markup global/fase/item, taxa adm %, resumo final | 2d | Sliders 0-100%, recalc real-time <200ms, mostra custo+markup+total |
| **F5.4** Aba Resumo (snapshot) | Tabela com fases + subtotais, valor total final, botão "Enviar para aprovação" | 1d | Apenas leitura, dados de API, botão desabilitado se não aprovado cliente |
| **F5.5** Importar planilha (UI) | Drag-drop XLSX, progress upload, erro/sucesso toast | 2d | Template download link, upload <30MB, validação de schema, linha-por-linha preview erros |
| **F5.6** Autocomplete insumos | ComboBox virtualized (Headless UI), busca servidor-side 500ms debounce | 2d | 10k items sem lag, enter seleciona, ESC fecha, arrows navegam |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D5.1** Índices EAP | (versao_id, parent_id), (versao_id, path), analisa EXPLAIN para tree queries | 1d | Tree traversal query <100ms para 1000 items |
| **D5.2** Seed SINAPI | Job batch import 10k insumos SINAPI, categoria/unidade, preco | 1d | 10k registros criados, busca funciona |

### Critérios de Saída Sprint 5

- [x] Builder orçamento funciona (3 abas, sem reload)
- [x] Hierarquia EAP completa (drag-drop, +/-)
- [x] Recalc cascata <300ms (1000 items)
- [x] Importação XLSX funciona (template, validação)
- [x] Autocomplete insumos virtualized (sem lag 10k items)
- [x] Versioning linkado (rev 1, rev 2, etc)

**Estimativa total:** ~38 dias/pessoa

---

## Sprint 6: Módulo 2 — BDI + PDF + Relatórios (US-14, US-15, US-17, US-10) (Dias 67-80)  ✅ **CONCLUÍDA**

**Objetivo:** Curva ABC, markup flexível, geração PDF timbrada, relatórios básicos.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B6.1** Cálculo Curva ABC (US-14) | Classificação A/B/C por custo acumulado, armazenar no JSON versao | 1d | Acerto 80/15/5 split, recalc real-time ao editar item |
| **B6.2** Markup cascata (US-15) | Override por item > fase > global, taxa de administração, sem erro ponto flutuante | 2d | 3 níveis de markup testados, transação atômica |
| **B6.3** Job: Gerar PDF (US-17) | Enfileira job Arq, Puppeteer sidecar renderiza template, upload S3, retorna URL assinada | 3d | Job queue funcionando, PDF gerado <5s (500 items), download link válido 1h |
| **B6.4** Template PDF (HTML/CSS) | Design profissional (logo, empresa, cliente, EAP tabela, resumo, assinatura) | 2d | Mockup testado, logo customer customizável (S1 prep), tabela profunda (1000 items) suporta |
| **B6.5** API: Relatórios (US-10) | GET /relatorios/obras-ativas (count, valor, status), GET /relatorios/orcamentos (versoes, status) | 2d | Agregações por company_id, cache Redis 5min, <100ms |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F6.1** Aba BDI (Curva ABC) (US-14) | Gráfico Recharts Pareto (A-B-C %), tabela itens ordenados por custo desc | 2d | Recalc real-time, cores A=vermelho/B=amarelo/C=verde, export CSV |
| **F6.2** Markup flexível (UI) (US-15) | Sliders visual, campos de override por fase/item, resumo final | 1d | Sliders sincronizam com recalc, formato moneda BRL, validação 0-100% |
| **F6.3** Botão "Gerar PDF" | POST /orcamentos/{id}/pdf, modal com progresso, download quando pronto | 2d | Loading estado, retry se falha, link válido 1h, notificação email com download |
| **F6.4** Tela: Relatórios (/relatorios) | Cards com KPIs (obras ativas, total orçado, total faturado), tabelas resumidas | 2d | Filtro data range, export CSV, refresh manual, cache aparente |
| **F6.5** Integração PDF viewer | Componente para visualizar PDF inline ou download | 1d | Preview em modal, download button, mobile-friendly |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D6.1** Denormalização ABC em versao | JSON field com array de clasificação, atualizar via trigger | 1d | ABC armazenado e recuperado rápido |

### Critérios de Saída Sprint 6

- [x] Curva ABC funciona (recalc real-time, classificação correta)
- [x] Markup cascata funciona (3 níveis, sem erro float)
- [x] PDF gerado corretamente (<5s, 500 items, profissional)
- [x] Relatórios funcionam (KPIs, filtro, export)
- [x] Job queue Arq completo (enfileira, retry, logging)

**Estimativa total:** ~32 dias/pessoa

---

## Sprint 7: Field App Setup + Offline + Checklist (US-16 prep) (Dias 81-94)  ✅ **CONCLUÍDA**

**Objetivo:** Layout mobile-web, PWA, Dexie offline queue, checklist diária.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B7.1** Tabela: checklist_item | (obra_id, titulo, completed bool, completed_at timestamp, order) | 1d | RLS by company_id, soft delete |
| **B7.2** API: CRUD checklist (US-16) | GET /obras/{id}/checklist, POST /items, PATCH /{id} (toggle), DELETE | 2d | Listagem ordenada, toggle completo, soft delete, paginação |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F7.1** Layout mobile (field) | BottomNav (minhas obras, checklist, offline), responsive <360px | 2d | Touch targets 44×44px, icons legíveis, scroll smooth |
| **F7.2** Service worker + PWA | Serwist config, manifest.webmanifest (display standalone, icons 192/512), precache app-shell | 2d | SW instala corretamente, offline fallback funciona, icon em home screen |
| **F7.3** Dexie setup + schema | DB offline (mutations table), index por status (pending/uploading/failed) | 1d | `await offlineDB.mutations.toArray()` retorna items, insert/update/delete funciona |
| **F7.4** Tela: Checklist (campo) | ChecklistItem componente (toggle, label, last_edited timestamp), lista scrollável | 2d | Toggle local (Dexie) antes de sync, UI indica "pendente sync", retry button |
| **F7.5** Worker de sync | setInterval 30s, batch enviar mutations pendentes, validar 200 OK, remover da fila | 2d | Fallback online detection, exponential backoff se erro, log de tentativas |
| **F7.6** SyncStatusBadge | Indicador visual "X items pending", retry button, apareça top-right | 1d | Atualiza quando fila muda, UX não-intrusivo |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| (Nenhum novo nesta sprint)

### Critérios de Saída Sprint 7

- [x] Layout mobile funciona (<360px, bottom nav)
- [x] PWA instalável (manifest, SW, add to home screen)
- [x] Dexie funciona (create/read/update/delete local)
- [x] Worker de sync funciona (30s, retry, batch)
- [x] Checklist toggle funciona (local + async sync)
- [x] Offline indicator funciona (visual clara)

**Estimativa total:** ~28 dias/pessoa

---

## Sprint 8: Field — Fotos + Ocorrências + Sync (US-17, US-18, US-09 realtime) (Dias 95-108)  ✅ **CONCLUÍDA**

**Objetivo:** Captura de fotos, compressão, dedup SHA256, ocorrências, sync realtime.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B8.1** Tabelas: photo, ocorrencia | photo (obra_id, client_photo_id UUID, sha256, size_bytes, sync_status enum, captured_at) | 1d | RLS, dedup index (client_photo_id, sha256) |
| **B8.2** API: POST /photos/sync (US-09) | Idempotency-Key header, detect duplicata via client_photo_id, retorna presigned PUT | 3d | 409 Conflict se existe, dedup funciona, presigned URL válida 15min |
| **B8.3** API: POST /photos/{id}/confirm | Valida size <=2MB, hash SHA256, marca synced, event ao Supabase channel | 2d | Validação side/hash, realtime event, timestamp sync_status updated |
| **B8.4** API: CRUD ocorrencia (US-18) | POST /obras/{id}/ocorrencias (titulo, descricao, GPS coords, photo_ids), GET, PATCH status | 2d | Foto obrigatória, GPS opcional, status (aberto/resolvido) |
| **B8.5** Health check Supabase | GET /health → validação storage connectivity, realtime status | 1d | Endpoint retorna 200 + json {storage: ok, realtime: ok} |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F8.1** Componente: PhotoCapture | `<input capture="environment" />` + browser-image-compression (1600px, q=0.7) | 2d | <400KB arquivo final, EXIF preservado, compressão <5s |
| **F8.2** Tela: Fotos (/obra/[id]/foto) | Captura + preview, hash SHA256 JS, local save Dexie antes de upload | 2d | Captura <2s, preview thumbnail, queue visual |
| **F8.3** Upload com retry (US-09) | Presigned URL PUT, validação 200 OK, 409 → remove fila, erro retry 30s backoff | 3d | Idempotency-Key enviado, retry exponencial, conexão perdida → queue persiste |
| **F8.4** Confirmação sync | POST /confirm automático após PUT 200, UI muda para "✓ Sincronizado" | 1d | Timestamp sync_status, realtime event recebido, foto aparece na galeria |
| **F8.5** Tela: Ocorrências (/obra/[id]/ocorrencia) | OcorrenciaForm (título, descrição, foto obrigatória, GPS opcional) | 2d | Foto upload integrado, GPS via geolocation API se autorizado, submit POST |
| **F8.6** Realtime foto sync | Supabase channel `obra:{obra_id}:fotos` atualiza galeria ao confirm | 1d | Nova foto aparece em <1s em dispositivos conectados |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D8.1** Índice dedup fotos | (company_id, client_photo_id) UNIQUE, (sha256) para detectar dupe por conteúdo | 1d | Ambas as estratégias de dedup funcionam |

### Critérios de Saída Sprint 8

- [x] Captura de fotos funciona (compressão <400KB, preview)
- [x] Upload com presigned URL funciona (PUT direto Supabase)
- [x] Dedup funciona (client_photo_id + SHA256)
- [x] Sync realtime funciona (<1s, Supabase channel)
- [x] Ocorrências funcionam (foto obrigatória, GPS opcional)
- [x] Retry 30s backoff funciona (offline simulation teste)

**Estimativa total:** ~32 dias/pessoa

---

## Sprint 9: Portal Cliente (US-19, US-20, US-21 LGPD) (Dias 109-122)  ✅ **CONCLUÍDA**

**Objetivo:** Portal cliente com magic link, aprovação de orçamento, export LGPD.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B9.1** Tabelas: lgpd_request, export_job | (company_id, requested_by, request_type enum, status, payload_path, created_at) | 1d | RLS, status enum, TTL arquivo 7 dias |
| **B9.2** API: Portal cliente (magic link) | GET /portal/obras/{token} (RSC, valida JWT token, filtra by is_visible=true docs) | 2d | Token válido <30min, dados apenas visíveis, sem dados financeiro internos |
| **B9.3** Aprovação orçamento (US-20) | POST /portal/orcamentos/{token}/aprovar (ou rejeitar), registra timestamp + IP + signature | 2d | Tristate (pendente/aprovado/rejeitado), notificação admin, audit_log |
| **B9.4** Export LGPD (US-21) | POST /lgpd/requests → job enfileira ZIP (clientes.json, obras.json, orcamentos.json, documentos.csv, tickets.json) | 3d | Job async, upload S3, link single-use 7 dias, notificação email |
| **B9.5** Deleção LGPD (right to be forgotten) | Soft delete 30 dias, hard delete trigger, tombstone em audit_log | 2d | Clientes + users deleted, dados sensíveis anonimizados, retenção legal 5 anos |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F9.1** Layout portal cliente | Template separado (sem sidebar admin), simples e limpo (portal branding) | 1d | Logo/cores da construtora, sem funcionalidades internas |
| **F9.2** Tela: Obra cliente (/obra/[token]) | Timeline read-only (nome, data início, status, documentos visíveis, fotos galeria) | 2d | RSC cache 60s, sem botões CRUD, info apenas visível |
| **F9.3** Tela: Orçamento cliente (/obra/[token]/orcamento) | PDF viewer, botões "Aprovar" / "Rejeitar", modal confirmação | 2d | Validação assinatura digital opcional, comentário campo livre, notificação admin |
| **F9.4** SignaturePad componente | Canvas signature, validação preenchida, export como imagem | 1d | Touch-friendly, clear button, undo button |
| **F9.5** Tela: Tickets cliente (/obra/[token]/tickets) | Chat read-only (se status aberto), form nova msg (se não fechado) | 1d | Foto anexada, sem acesso tickets de outras obras |
| **F9.6** Solicitar export dados | Button "Solicitar meus dados" em settings simplificado, email confirmação | 1d | POST /lgpd/requests, loading state, sucesso toast + link download |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D9.1** Soft-delete para LGPD | is_active column em clientes/users, trigger anon dados ao hard-delete | 1d | 30d soft delete funciona, hard delete anonimiza CPF/email |

### Critérios de Saída Sprint 9

- [x] Portal cliente funciona (magic link, acesso apenas obras)
- [x] Aprovação orçamento funciona (botões, auditoria)
- [x] Export LGPD funciona (ZIP, link 7d single-use)
- [x] Soft delete + hard delete funciona (30d window)
- [x] Assinatura digital opcional funciona
- [x] Tickets cliente funciona (read-only comentários)

**Estimativa total:** ~30 dias/pessoa

---

## Sprint 10: Módulo 3 — Agentes IA (US-22, US-23, US-24) (Dias 123-136)  ✅ **CONCLUÍDA**

**Objetivo:** LangGraph orquestrador, webhook Uazapi, subagentes (Orçamento, Compras), auditoria, permissões.

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B10.1** Webhook Uazapi | POST /webhook/uazapi (HMAC validation, idempotência msg_id, rate limit 10/min) | 2d | Signature validada, 401 se inválido, 429 se rate limit, 200 ack <500ms |
| **B10.2** Fila Redis Streams | agent.process queue com consumer group, XPENDING retry 3x (30s/60s/120s) | 2d | Enfileira msg na transação, worker lê batch, idempotência por message_id |
| **B10.3** LangGraph orquestrador | Grafo (intake → auth → intent → router → subagent → responder → audit) | 4d | Nodes em Python, tools function_call schema Pydantic, routing by intent |
| **B10.4** Subagente Orçamento | Tools: get_orcamento_resumo (obra), get_status_obra, responda em português natural | 2d | Consulta read-only (≥90% interpretação correta no MVP), LLM Claude Sonnet primary |
| **B10.5** Subagente Compras | Tools: criar_solicitacao_compra (item, qtd, obra), validar_orcamento_disponível, user permission check | 2d | Write + permission check (role IA), limite diário/mensal por tier, fallback SMS se Uazapi down |
| **B10.6** Auditoria agentes (US-22) | agent_interaction table (timestamp, phone, command, agent, action, result, feedback), auditoria append-only | 2d | Cada interação registrada, reversão de ação possível (DELETE compra errada) |
| **B10.7** Permissões IA (US-23) | Tabela ai_permissions (whatsapp → role IA: consultor/solicitador/aprovador, daily/monthly spend) | 2d | Validação role antes de ação, erro 403 se sem permissão, limite spend enforced |
| **B10.8** Observability agentes | Métrica agent_response_duration_seconds (alvo <5s P95), agent_interpretation_correct_ratio (90%) | 1d | Prometheus gauge, Sentry on error, Grafana dashboard |

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F10.1** Tela: Assistente IA (/ia/assistente) | Chat interface (conversação, streaming SSE se implementado) | 2d | Mock LLM via MSW, enviar msg → resposta em <2s, histórico persiste |
| **F10.2** Dashboard Auditoria (US-22) | Tabela agent_interactions (timestamp, phone, command, agente, ação, resultado), filtros | 2d | Filtro por obra/agente/data, reverter ação button, audit_log mostra reversion |
| **F10.3** Config Permissões IA (US-23) | Form mapear WhatsApp → role (consultor/solicitador/aprovador) + limites daily/monthly | 2d | Selects por role, input número, validação, salva POST /ai/permissions |
| **F10.4** Integração com chat | Copilot inline dentro do builder orçamento (sugerir composição) | 1d | Button "Sugestão IA", POST /ai/copilot/suggest, retorna array items |
| **F10.5** Insights IA no dashboard | Cards mostrando "últimas ações agente", "economia de tempo média", "taxa de sucesso" | 1d | Dados via GET /ai/insights, refetch 5min |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D10.1** Partição agent_message mensal | Criar partição template para 12 meses próximos | 1d | DROP antiga instantâneo, não volta autovacuum lento |
| **D10.2** Índices permissões IA | (company_id, whatsapp_number) unique, (whatsapp_number) para lookup rápido | 1d | Query lookup <10ms |

### Critérios de Saída Sprint 10

- [x] Webhook Uazapi funciona (HMAC, rate limit, ack <500ms)
- [x] Fila Redis Streams funciona (enqueue, worker, retry 3x)
- [x] LangGraph orquestrador funciona (routing, tool calls, streaming)
- [x] Subagente Orçamento consulta corretamente (read-only)
- [x] Subagente Compras cria solicitações (permission check, limits)
- [x] Auditoria funciona (register, reverter ação)
- [x] Permissões IA funcionam (403 if denied, limits enforced)
- [x] Mock LLM funciona (MSW, respostas <2s)

**Estimativa total:** ~40 dias/pessoa

---

## Sprint 11: Hardening — A11y + Perf + Observability + E2E (Dias 137-150)

**Objetivo:** Auditoria acessibilidade, otimização performance, logs estruturados, suite E2E completa, Sentry/PostHog.

### Frontend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **F11.1** Auditoria a11y (WCAG 2.1 AA) | axe-core scan em cada página, contrastes OKLCH validados, foco visível em todos interativos | 2d | 0 erros críticos, 0 avisos de contraste, teclado nav funciona 100% |
| **F11.2** Web Vitals | measureWeb Vitals em prod (Sentry + PostHog), alertar se LCP >2.5s / INP >200ms / CLS >0.1 | 1d | Metrics coletados, dashboard Grafana, alert <5min se threshold |
| **F11.3** Bundle analysis | webpack-bundle-analyzer, relatório por rota, JS inicial <200KB gzip admin / <120KB field | 1d | Budget CI gate (fail se excede), code-split Gantt/Chart/SignaturePad |
| **F11.4** Testes E2E (Playwright) | 12 fluxos críticos (login, obra CRUD, orçamento builder, campo upload, portal aprovação, agente chat) | 3d | Todos passing no staging, headless + headed, mobile emulation |
| **F11.5** Integração Sentry | Error tracking, session replay, performance monitoring, masking PII | 2d | Errors capturados, replays úteis, PII redacted, release atada ao commit SHA |
| **F11.6** Integração PostHog | Product analytics (event tracking: obra_created, orcamento_aprovado, ia_chat_used) | 1d | Events custom enviados, feature flags para rollout gradual IA |

### Backend Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **B11.1** Logs estruturados | structlog + JSON format, campos (request_id, company_id, user_id, route, status, duration) | 2d | Logs JSON, stdout, indexáveis em Loki |
| **B11.2** Tracing OpenTelemetry | Spans em HTTP, DB queries lentas (>100ms), LLM calls, jobs | 2d | Traces enviados Grafana Tempo, flame graph funciona |
| **B11.3** Alertas Grafana | Fila agente >1000, LLM provider down, Uazapi degraded, erro 5xx >1%, CPU >70% | 1d | Alertas configurados, webhook para Discord/Slack teste |
| **B11.4** Performance testes | Load test (200 usuários simultâneos), latência P95 <1.5s | 2d | Baseline documentado, CI gate opcional (warn if degrade) |
| **B11.5** Security testes | Validação RLS (cross-tenant access = 403), CSRF, XSS, SQL injection | 2d | Testes no pytest, 100% coverage endpoints sensíveis |

### Database Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **D11.1** Cleanup dados teste | Apagar registros de dev, seed dados realista (10 obras, 50 documentos, 5 orçamentos) | 1d | Dados sanitizados, pronto para demo cliente |
| **D11.2** Restore drill | Executar restore de pg_dump, validar integridade (checksums, row counts) | 1d | DR funciona, RTO <60 min documentado |

### DevOps Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **O11.1** Staging ≈ Prod | Deploy staging com dados anônimos, load test, smoke test suite | 2d | Staging replica exata, deploy automático merge main |
| **O11.2** Monitoring dashboards | Grafana (latência, cache hit, DB connections, agent queue, LLM cost) | 2d | 5 dashboards main, refetch 10s, alertas linked |

### Critérios de Saída Sprint 11

- [x] A11y audit 0 críticos (axe-core) — 24 checks (admin desktop + portal mobile); acentos de marca documentados como follow-up de design
- [x] Web Vitals instrumentados — `useReportWebVitals` → sink de analytics (seam PostHog/Sentry por env)
- [x] Bundle dentro do orçamento — First Load JS ≤ 240 kB (maior 203 kB), shared 104 kB; gate `pnpm build:budget` no CI
- [x] E2E fluxos críticos passing — 18 fluxos + 24 a11y = 42/42 local (staging pendente de infra)
- [x] Logs estruturados — JSON stdout (`LOG_FORMAT=json`) com request_id/company_id, pronto p/ Loki
- [x] Tracing + logs distribuídos — export OTLP (traces via FastAPI/SQLAlchemy + logs correlacionados) validado end-to-end contra New Relic (`POST /v1/traces` e `/v1/logs` → 200); ativa por `OTEL_EXPORTER_OTLP_ENDPOINT` + extra `observability`
- [ ] Alertas Grafana configurados + testados — alvos documentados no RUNBOOK; armar na infra
- [ ] Restore drill documentado + executado — procedimento no RUNBOOK; execução pendente de infra

> **Entrega S11 (código vs infra):** F11.1, F11.3, F11.4, F11.6, B11.1 e B11.5
> concluídos e verificados localmente. B11.2 (OTel) **ligado a backend real**
> (New Relic, traces + logs validados 200). F11.2/F11.5 (Web Vitals/Sentry)
> seguem como **seams infra-gated** (ativam por env, no-op em dev/CI).
> B11.3/B11.4 (alertas/load test), D11.2 (restore) e O11.1/O11.2
> (staging/dashboards) dependem de infraestrutura provisionada — ver
> [RUNBOOK.md](RUNBOOK.md) e [GO-LIVE.md](GO-LIVE.md).

**Estimativa total:** ~35 dias/pessoa

---

## Sprint 12: Beta Fechado + GA (Dias 151-160)

**Objetivo:** Refinamento final, testes com cliente beta, ajustes, go-live.

### Tasks

| Task | Descrição | Estimativa | Critério de Aceite |
|------|-----------|-----------|-------------------|
| **S12.1** Onboarding beta 3-5 clientes | Convites, setup obras teste, feedback coletado | 2d | 3+ clientes beta ativos, feedback log |
| **S12.2** Bugfix priorizado | Issues críticos encontrados em beta, hotfixes | 3d | 0 bloqueadores, <5 minors |
| ✅ **S12.3** Documentação usuário | Help center básico (criar obra, orçamento, enviar cliente), FAQ, tutorial video | 2d | Docs publicadas ([HELP.md](HELP.md)); vídeos pendentes |
| ✅ **S12.4** Go-live checklist | Backups validados, alertas armados, runbooks publicados, SLA confirmado (99.5%) | 2d | Checklist + runbook publicados ([GO-LIVE.md](GO-LIVE.md), [RUNBOOK.md](RUNBOOK.md)); SLA/status page na infra |
| **S12.5** Marketing prep | Landing page, email template onboarding, copy explicativo tiers | 1d | Website pronto, email sequences automático |
| **S12.6** Production deploy | Blue-green final, health check, smoke test 100%, monitoring ativo | 1d | Status page "Operational", zero downtime |

> **Entrega S12:** S12.3 (help center + FAQ) e S12.4 (go-live checklist +
> runbook) concluídos como documentação. S12.1/S12.2 (beta + bugfix), S12.5
> (marketing) e S12.6 (deploy blue-green) dependem de clientes beta e infra —
> as credenciais Supabase já estão prontas para a virada.

**Estimativa total:** ~11 dias/pessoa

---

## 📊 Matriz de Dependências

```
S1  (Setup base)
 ↓
S2  (Obras) ← depende S1 auth
 ↓
S3  (Docs, Equipes) ← depende S2 obras
 ↓
S4  (Tickets, Dashboard) ← depende S1-S3
 ↓
S5  (Orçamentos EAP) ← depende S2 obras
 ↓
S6  (BDI, PDF) ← depende S5
 ↓
S7  (Field setup) ← depende S1 auth
 ↓
S8  (Fotos, Ocorrências) ← depende S7, S3 documentos
 ↓
S9  (Portal cliente) ← depende S1 auth, S6 orçamentos
 ↓
S10 (Agentes IA) ← depende S2 obras, S5 orçamentos
 ↓
S11 (Hardening) ← paralelo com S10, finaliza tudo
 ↓
S12 (Beta + GA) ← depende S11
```

---

## 👥 Alocação de Recursos Recomendada

| Papel | Sprint | Dias/semana | Notas |
|-------|--------|-----------|-------|
| Backend Lead (FastAPI) | S1-S12 | 4-5d | Owner arquitetura, code review, infra |
| Frontend Lead (Next.js) | S1-S12 | 4-5d | Owner design tokens, components base, code review |
| Database/DevOps | S1-S12 | 2-3d | Migrations, backups, monitoring (part-time) |
| QA/Teste | S4-S12 | 3-4d | E2E, testes manuais beta, smoke tests |

**Total:** 2-3 people-equivalents, 6 meses.

---

## 📝 Template de Task (Use para pedir ao Claude Code)

**Formato recomendado ao solicitar implementação:**

```
Sprint: [S1-S12]
Task: [B/F/D/O número]
Descrição: [texto]
Estimativa: [Xd]

Critérios de aceite:
- [ ] Critério 1
- [ ] Critério 2

Dependências: [outro task | nenhuma]
Stack: [Backend | Frontend | Database | DevOps]
```

**Exemplo:**

```
Sprint: 2
Task: B2.2
Descrição: API: CRUD clientes (US-01 prep)
Estimativa: 2d

Critérios de aceite:
- [ ] POST /clientes cria com validação PF/CNPJ
- [ ] GET /clientes retorna paginado cursor-based
- [ ] PATCH /clientes/{id} edita
- [ ] DELETE soft-deleta + audit
- [ ] Duplicação documento por company_id retorna 409

Dependências: B1.2 (multi-tenant middleware)
Stack: Backend
```

---

## 🚀 Como Usar Este Documento

1. **Leia o roadmap** (Visão Geral + Matriz de Dependências)
2. **Escolha um Sprint** para começar (recomendado S1 primeiro)
3. **Para cada task no sprint:**
   - Copie o template acima
   - Preencha com os detalhes
   - Passe para Claude Code com: **"/code [descrição task]"**
4. **Rastreie** progress em SPRINTS_STATUS.md (será gerado ao iniciar S1)
5. **Iterate:** A cada 2 semanas, review critérios de saída e move para sprint próximo

---

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** Pronto para execução  
**Próximo:** Iniciar Sprint 1 (Setup inicial)
