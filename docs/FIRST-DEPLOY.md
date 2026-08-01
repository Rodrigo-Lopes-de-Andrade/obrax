# Primeiro Deploy — Obrax (passo a passo)

Sequência linear e copiável para a **primeira virada de produção**. Complementa o
[GO-LIVE.md](GO-LIVE.md) (checklist de aceite) e o [RUNBOOK.md](RUNBOOK.md)
(referência). Tudo que é código já está pronto — aqui é só provisionar e virar.

> Convenção: `<...>` são valores que você preenche. Nunca commite secrets.

---

## 0. Pré-requisitos (contas + CLIs)

| Ferramenta | Para quê | Link |
|---|---|---|
| **flyctl** | Deploy do backend | https://fly.io/docs/flyctl/install/ |
| **Vercel CLI** | Deploy do frontend | https://vercel.com/docs/cli |
| **gh** (GitHub CLI) | Secrets do CI (O11.1) | https://cli.github.com/ |
| **uv** | Rodar os scripts do backend | https://docs.astral.sh/uv/ |
| Conta **Supabase** | Banco + Storage (já provisionada) | https://supabase.com/dashboard |
| Conta **New Relic** | Alertas + dashboard (dashboard já no ar) | https://one.newrelic.com/ |

```bash
fly auth login
vercel login
gh auth login
```

Arquivos que este guia usa (já no repo):
[backend/Dockerfile](../backend/Dockerfile) ·
[backend/fly.toml](../backend/fly.toml) ·
[frontend/vercel.json](../frontend/vercel.json) ·
[backend/scripts/smoke_test.py](../backend/scripts/smoke_test.py) ·
[backend/scripts/setup_nr_alerts.py](../backend/scripts/setup_nr_alerts.py) ·
[backend/scripts/setup_nr_dashboards.py](../backend/scripts/setup_nr_dashboards.py) ·
[.github/workflows/ci.yml](../.github/workflows/ci.yml)

---

## 1. Serviços gerenciados

1. **Buckets de Storage** (Supabase → Storage): crie `documents-prod`, `photos-prod`,
   `pdfs-prod`, `exports-prod`. Gere as credenciais **S3** (Storage → Settings → S3
   access keys) — viram os `STORAGE_*`.
2. **Sidecar de PDF** (container Puppeteer): suba e anote a URL → `PDF_RENDERER_URL`.
3. **Redis**: só se o **Módulo 3 (IA)** entrar no beta. Basic/Pro sem IA dispensa.

---

## 2. Backend → Fly.io

Ajuste `app`/`primary_region` em [backend/fly.toml](../backend/fly.toml) e crie o app:

```bash
cd backend
fly apps create <obrax-api>            # mesmo nome do campo `app` no fly.toml
```

Secrets (nunca no fly.toml — as envs **não-secretas** já estão lá):

```bash
fly secrets set --app <obrax-api> \
  JWT_SECRET="<gerar: openssl rand -hex 32>" \
  DATABASE_URL="postgresql://app_user.<ref>:<senha%40enc>@aws-0-<reg>.pooler.supabase.com:6543/postgres?pgbouncer=true" \
  APP_USER_DATABASE_URL="postgresql://app_user.<ref>:<senha%40enc>@...:6543/postgres?pgbouncer=true" \
  APP_ADMIN_DATABASE_URL="postgresql://app_admin.<ref>:<senha%40enc>@...:6543/postgres?pgbouncer=true" \
  SUPABASE_DB_URL_MIGRATIONS="postgresql://postgres.<ref>:<senha%40enc>@aws-0-<reg>.pooler.supabase.com:5432/postgres" \
  SUPABASE_URL="https://<ref>.supabase.co" \
  SUPABASE_SERVICE_KEY="<service-role-key>" \
  STORAGE_ENDPOINT_URL="https://<ref>.supabase.co/storage/v1/s3" \
  STORAGE_REGION="<reg>" \
  STORAGE_ACCESS_KEY="<s3-access-key>" \
  STORAGE_SECRET_KEY="<s3-secret-key>" \
  STORAGE_BUCKET_DOCUMENTS="documents-prod" \
  PDF_RENDERER_URL="<url-do-sidecar>" \
  OTEL_EXPORTER_OTLP_HEADERS="api-key=<license-key-NRAL>"
  # Módulo 3 (se no beta): UAZAPI_WEBHOOK_SECRET, UAZAPI_BASE_URL, UAZAPI_TOKEN
```

> ⚠️ **Senha do DSN** com caractere especial precisa ser **percent-encoded**
> (`@`→`%40`). `DATABASE_URL` usa o **transaction pooler `:6543`**;
> `SUPABASE_DB_URL_MIGRATIONS` usa o **session pooler `:5432`** (as migrations
> rodam no `release_command` do fly.toml). Ver [RUNBOOK §2](RUNBOOK.md).

Deploy (as migrations rodam sozinhas no `release_command`, antes da troca):

```bash
fly deploy --app <obrax-api>
```

---

## 3. Frontend → Vercel

```bash
cd frontend
vercel link            # selecione/crie o projeto; Root Directory = frontend
```

Envs do projeto (Vercel → Settings → Environment Variables, ambiente **Production**):

| Variável | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<obrax-api>.fly.dev` (ou o domínio da API) |
| `NEXT_PUBLIC_POSTHOG_KEY` | `<posthog key>` |
| `NEXT_PUBLIC_SENTRY_DSN` | `<sentry dsn>` |

```bash
vercel deploy --prod   # build roda pnpm build:budget (gate de bundle)
```

---

## 4. Observabilidade (New Relic)

```bash
cd backend
uv run python -m scripts.setup_nr_alerts --apply       # arma a policy + 4 condições
uv run python -m scripts.setup_nr_dashboards --apply    # dashboard (já no ar; converge)
```

**Manual no console** New Relic: anexar um **canal de notificação** (webhook
Discord/Slack) à policy `Obrax API — SLO`. Ver [RUNBOOK §4](RUNBOOK.md).

---

## 5. Smoke test contra produção

Gate final antes de anunciar. Read-only, seguro:

```bash
cd backend
uv run python -m scripts.smoke_test \
  --api-url https://<obrax-api>.fly.dev \
  --frontend-url https://<obrax>.vercel.app \
  --require-storage
```

Sai `!= 0` se qualquer gate falhar (`/health`, `/openapi.json`, rota protegida
exige 401). **Não anuncie o go-live se falhar.**

---

## 6. CI + deploy automático de staging (O11.1)

Para o [.github/workflows/ci.yml](../.github/workflows/ci.yml) deployar staging no
merge para `main`, configure os secrets/vars no repo GitHub:

```bash
gh secret set FLY_API_TOKEN_STAGING       # fly tokens create deploy -a <obrax-api-staging>
gh secret set VERCEL_TOKEN
gh secret set VERCEL_ORG_ID
gh secret set VERCEL_PROJECT_ID
gh variable set FLY_STAGING_APP     --body "<obrax-api-staging>"
gh variable set STAGING_API_URL     --body "https://<obrax-api-staging>.fly.dev"
gh variable set STAGING_FRONTEND_URL --body "https://<staging>.vercel.app"
```

Repita a Fase 2/3 com um app/projeto **de staging** separado (`obrax-api-staging`).

---

## 7. Go-live + rollback

- Rode o checklist de aceite: [GO-LIVE.md](GO-LIVE.md).
- Procedimento **blue-green** completo (green → smoke → cutover → monitorar 60 min →
  rollback): [RUNBOOK §3](RUNBOOK.md).
- Status page → **Operational**.

**Rollback rápido:** reponte o tráfego green → blue (o blue segue de pé nos
primeiros 60 min). Migrations são expand-contract, então o blue continua
compatível com o schema novo.
