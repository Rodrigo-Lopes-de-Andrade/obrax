# Runbook Operacional — Obrax

Guia de operação para deploy, configuração, observabilidade e resposta a
incidentes. Público: quem opera a plataforma (DevOps/on-call). Complementa
[GO-LIVE.md](GO-LIVE.md) (checklist de virada) e [ESPEC.md](ESPEC.md) (contrato
técnico).

---

## 1. Arquitetura em uma tela

| Camada | Stack | Notas |
|---|---|---|
| Frontend | Next.js 15 (App Router), PWA (Serwist) | Mock-first via MSW **só em dev**; prod fala com a API real |
| Backend | FastAPI (async), SQLAlchemy + psycopg 3 | RFC 7807 para erros; RLS por tenant |
| Banco | PostgreSQL (Supabase) | Multi-tenant via RLS + `SET LOCAL app.company_id` |
| Storage | S3-compatível (Supabase Storage / MinIO em dev) | Presigned PUT/GET |
| Fila de agentes | In-process (dev/CI) → externa em prod | Módulo 3 (WhatsApp/Uazapi) |

### Multi-tenancy (crítico)
Todo dado de tenant é isolado por **Row-Level Security**. A cada request:
1. `TenantMiddleware` decodifica o JWT e popula `request.state.auth`.
2. `get_db` abre a transação e roda `SET LOCAL app.company_id = <company>`.
3. As policies `USING/WITH CHECK (company_id = current_setting('app.company_id'))`
   filtram leitura **e** escrita.

Dois roles no Postgres: `app_user` (sujeito a RLS, runtime da API) e `app_admin`
(BYPASSRLS, só para fluxos pré-tenant: login, aceitar convite). **Nunca** rode a
API como `app_admin`.

---

## 2. Variáveis de ambiente

### Backend
| Variável | Obrigatória | Default | Função |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | DSN base (deriva `app_user`/`app_admin` se os DSNs explícitos não forem dados) |
| `APP_USER_DATABASE_URL` | prod | derivado | DSN de runtime (role `app_user`) |
| `APP_ADMIN_DATABASE_URL` | prod | derivado | DSN administrativa (role `app_admin`) |
| `JWT_SECRET` | ✅ | — | Assinatura dos tokens de acesso/refresh |
| `ENVIRONMENT` | ✅ | `development` | `production` liga `Secure` no cookie de refresh |
| `LOG_FORMAT` | — | texto | `json` → linhas JSON para Loki/Datadog |
| `LOG_LEVEL` | — | `INFO` | Nível do root logger |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | — | Liga o tracing OTel (requer pacotes `opentelemetry-*`) |
| `STORAGE_*` | prod | MinIO local | Endpoint/credenciais/bucket do object store |
| `REALTIME_ENABLED` + `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | prod | off | Realtime do chat de tickets |
| `PDF_RENDERER_URL` | prod | dev-renderer | Sidecar HTML→PDF do orçamento |
| `UAZAPI_WEBHOOK_SECRET` | Módulo 3 | vazio (fail-closed) | Valida o HMAC do webhook do WhatsApp |
| `UAZAPI_BASE_URL` / `UAZAPI_TOKEN` | Módulo 3 | vazio (no-op) | Cliente de envio Uazapi (API não-oficial do WhatsApp — https://uazapi.dev/) |

### Frontend (`NEXT_PUBLIC_*`, expostas ao browser — nunca secrets)
| Variável | Default | Função |
|---|---|---|
| `NEXT_PUBLIC_POSTHOG_KEY` | — | Liga analytics de produto (F11.6). Sem ela, `capture()` é no-op |
| `NEXT_PUBLIC_POSTHOG_HOST` | `https://us.i.posthog.com` | Host do PostHog |
| `NEXT_PUBLIC_SENTRY_DSN` | — | Rota de erros dedicada (F11.5); ver `lib/observability/errors.ts` |

> ⚠️ **Gotcha de DSN Supabase**: se a senha do banco contém caracteres especiais
> (`[ ] @ / : # ?`), ela **precisa** ser percent-encoded na URL (ex.: `@`→`%40`),
> senão o `urllib`/psycopg falha no parse do host. Sintoma:
> `ValueError: '<host>' does not appear to be an IPv4 or IPv6 address`. O Alembic
> (`env.py`) já escapa `%`→`%%` para o ConfigParser não interpretar a senha.

> ℹ️ **Pooler & prepared statements**: no *transaction pooler* (`:6543` /
> `?pgbouncer=true`) o `db.py` desliga automaticamente os prepared statements do
> psycopg3 (`prepare_threshold=None`) — obrigatório com pgbouncer. Migrations usam
> o *session pooler* (`:5432`), que mantém o default.

---

## 3. Deploy

### Migrations (rodar **antes** de subir a app)
Use a **session pooler** (porta 5432), não a transaction pooler (6543) —
migrations precisam de features de sessão/locks.
```bash
cd backend
DATABASE_URL="$SUPABASE_DB_URL_MIGRATIONS" alembic upgrade head
```
Migrations são forward-only e sequenciais (`0001`…`00NN`). Nunca edite uma
migration já aplicada; crie a próxima.

### App
```bash
# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000   # configure_logging roda no factory

# Frontend
cd frontend && pnpm build && pnpm start            # sem MSW em prod
```

### Gate de bundle no CI (F11.3)
```bash
cd frontend && pnpm build:budget   # reprova rota > 240 kB First Load JS (shared > 130 kB)
```

### Health check
`GET /health` → `{status, storage, realtime}`. É relatório (sempre 200), não gate;
use-o no readiness probe verificando `status == "ok"`.

---

## 4. Observabilidade

- **Logs** (B11.1): JSON em stdout com `LOG_FORMAT=json`. Cada linha carrega
  `request_id` (também devolvido no header `X-Request-Id`) e `company_id`. Uma
  linha de acesso por request com método, rota, status e `duration_ms`.
- **Tracing** (B11.2): setar `OTEL_EXPORTER_OTLP_ENDPOINT` + instalar
  `opentelemetry-instrumentation-fastapi` → spans para Tempo. Sem isso, no-op.
- **Web Vitals** (F11.5): reportados via `useReportWebVitals` para o sink de
  analytics (`$web_vitals`). Thresholds de alerta: LCP > 2.5s, INP > 200ms, CLS > 0.1.
- **Erros** (F11.5): handlers globais (`window.onerror`/`unhandledrejection`) →
  `captureError`. Rota de produção dedicada = instalar `@sentry/nextjs` e ligar
  em `errors.ts` sob `NEXT_PUBLIC_SENTRY_DSN`.
- **Analytics** (F11.6): eventos de produto via `capture()` (ex.:
  `assistente_mensagem_enviada`, `lgpd_pedido_criado`).

### Alertas a armar (B11.3)
Fila de agentes > 1000 · LLM provider down · Uazapi degradado · 5xx > 1% ·
CPU > 70% · Web Vitals acima do threshold. Webhook → Discord/Slack.

---

## 5. Backup & restore (D11.2 — RTO < 60 min)

- Backups gerenciados pelo Supabase (PITR). Validar retenção e um restore real
  em staging periodicamente (restore drill).
- Restore manual: `pg_restore` do dump mais recente em uma instância limpa,
  conferir `row_counts`/checksums das tabelas principais, repontar a app.
- **RTO alvo: < 60 min. RPO: conforme janela de PITR.**

---

## 6. Resposta a incidentes (playbooks)

| Sintoma | Primeiro diagnóstico | Ação |
|---|---|---|
| 5xx em alta | Logs por `request_id`; `/health` (storage/realtime) | Rollback do último deploy; checar migrations pendentes |
| "Sem company_id no contexto" (401 em massa) | JWT/`JWT_SECRET` rotacionado? relógio? | Reverter rotação; validar clock skew |
| Vazamento cross-tenant suspeito | Rodar `pytest tests/test_rls_isolation.py tests/test_agentes_rls.py` no staging | Congelar deploy; auditar policy RLS da tabela |
| Fila de agentes travada | Métrica de profundidade + dead-letter | Drenar dead-letter; checar Uazapi/LLM |
| Storage error no `/health` | Credenciais/bucket/endpoint | Repor `STORAGE_*`; validar presign |

---

## 7. Segurança

- RLS é a fronteira de tenant — coberta por `tests/test_rls_isolation.py` e
  `tests/test_agentes_rls.py` (Módulo 3). Rode-os no CI contra Postgres real.
- Webhook do Uazapi é **fail-closed**: sem `UAZAPI_WEBHOOK_SECRET`, rejeita tudo.
- Cookies de refresh: `Secure` + `HttpOnly` em produção (`ENVIRONMENT=production`).
- Secrets nunca em `NEXT_PUBLIC_*` (essas vão para o browser).
