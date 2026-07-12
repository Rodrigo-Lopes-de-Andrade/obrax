# Checklist de Go-Live — Obrax

Critérios de virada para produção (S12.4/S12.6). Marque cada item antes de abrir
para clientes. Detalhes operacionais em [RUNBOOK.md](RUNBOOK.md).

## Pré-requisitos de infraestrutura
- [ ] Banco de produção (Supabase) provisionado; `alembic upgrade head` aplicado (session pooler 5432).
- [ ] Roles `app_user` (RLS) e `app_admin` (BYPASSRLS) criados; DSNs em secrets manager.
- [ ] Senha do DSN **percent-encoded** se tiver caracteres especiais (ver gotcha no runbook).
- [ ] Object store (Supabase Storage) com bucket de documentos + credenciais; presign PUT/GET testado.
- [ ] `JWT_SECRET` forte e único de produção; `ENVIRONMENT=production`.
- [ ] Sidecar de PDF (`PDF_RENDERER_URL`) online; smoke de um orçamento → PDF.
- [ ] Módulo 3 (se ativo): `UAZAP_WEBHOOK_SECRET`, `UAZAP_BASE_URL`, `UAZAP_TOKEN`; webhook validando HMAC.

## Qualidade / testes (verde no CI)
- [ ] Backend: `ruff`, `mypy`, `pytest` (unit + integração DB + RLS) passando contra Postgres real.
- [ ] RLS cross-tenant validado: `tests/test_rls_isolation.py` + `tests/test_agentes_rls.py`.
- [ ] Frontend: `lint`, `tsc`, `build` limpos.
- [ ] E2E Playwright (`test:e2e`) verdes: fluxos críticos + a11y (WCAG 2.1 AA, 0 críticos).
- [ ] Bundle budget (`build:budget`) dentro do teto (rota ≤ 240 kB, shared ≤ 130 kB).

## Observabilidade & alertas
- [ ] `LOG_FORMAT=json`; logs chegando ao agregador (Loki/Datadog) com `request_id`/`company_id`.
- [ ] Tracing OTel ligado (`OTEL_EXPORTER_OTLP_ENDPOINT` + pacotes) → Tempo, se aplicável.
- [ ] Web Vitals + erros chegando ao PostHog/Sentry (`NEXT_PUBLIC_*` setadas).
- [ ] Alertas armados e **testados** (webhook dispara): 5xx > 1%, fila > 1000, Uazap/LLM down, CPU > 70%, Web Vitals.
- [ ] Dashboards Grafana publicados (latência, DB connections, fila de agentes, custo LLM).

## Dados & resiliência
- [ ] Dados de teste/dev removidos; seed realista para demo (se aplicável).
- [ ] Backups (PITR) confirmados; **restore drill** executado (RTO < 60 min documentado).
- [ ] Readiness probe usando `/health` (`status == "ok"`).

## Produto & suporte
- [ ] Help center publicado ([HELP.md](HELP.md)); FAQ acessível ao usuário.
- [ ] Canal de suporte definido; runbook de incidentes disponível ao on-call.
- [ ] SLA de disponibilidade confirmado (alvo 99,5%); status page pública.

## Virada (S12.6)
- [ ] Deploy blue-green; smoke test 100% no ambiente novo antes de repontar tráfego.
- [ ] Monitoramento ativo nos primeiros 60 min pós-virada; plano de rollback pronto.
- [ ] Status page em **Operational**; zero downtime confirmado.
