# Teste de Carga (B11.4)

Harness Locust para os fluxos de **leitura autenticados** mais quentes do painel
admin. Mede latência sob concorrência contra a meta de RNF.

- **Script:** [`backend/loadtest/locustfile.py`](../backend/loadtest/locustfile.py)
- **SLO alvo:** P95 < 1.5s sob 200 usuários simultâneos.
- **Escopo:** só `GET` + `POST /auth/login`. **Não escreve nada** — seguro contra staging.

## Fluxos exercitados

Uma `AdminReadUser` faz login uma vez e percorre as telas de leitura com pesos
que aproximam o uso real:

| Endpoint | Peso | Tela |
|----------|:----:|------|
| `GET /dashboard/summary` | 4 | Dashboard (KPIs) |
| `GET /obras` | 4 | Lista de obras |
| `GET /obras/{id}` | 3 | Detalhe de obra |
| `GET /clientes` | 2 | Lista de clientes |
| `GET /orcamentos` | 2 | Lista de orçamentos |
| `GET /tickets` | 1 | Lista de tickets |

`wait_time` de 1–3s entre requests (think time). Auth via `POST /auth/login`
(pega o JWT) e header `Authorization: Bearer` explícito em cada request.

## Como rodar

Precisa de um app FastAPI no ar e um usuário semeado. Exemplo apontando para o
staging (o seed demo cria `demo@obrax.com.br` / `obraxdemo123`):

```bash
cd backend
# 1. app local apontando para o banco alvo (staging aqui)
DATABASE_URL="postgresql://postgres.<ref>:<senha>@<pooler>:5432/postgres" \
  ENVIRONMENT=development JWT_SECRET="loadtest-secret" \
  .venv/bin/python -m uvicorn app.main:app --port 8000 &

# 2. carga alvo (200 usuários, rampa 20/s, 5 min)
LOADTEST_EMAIL=demo@obrax.com.br LOADTEST_PASSWORD=obraxdemo123 \
  .venv/bin/locust -f loadtest/locustfile.py --host http://localhost:8000 \
  --headless -u 200 -r 20 -t 5m
```

Interativo (UI web em :8089): omita `--headless -u -r -t`.

## Baseline

Validação executada (staging ca-central-1, app local via WSL, 10 usuários / 30s):

- **Corretude do harness:** 93 requests, **0.00% de falhas** em todos os endpoints.
- **Latência:** piso ~1.4s com variância mínima em todos os endpoints.

> ⚠️ **Esse número é network-bound, não representa o SLO.** O piso de ~1.4s é
> custo fixo de: (a) RTT WSL→ca-central-1 e (b) `NullPool` abrindo uma conexão
> nova no pooler a cada request (ver [db.py](../backend/app/core/db.py)). As
> queries em si são leituras indexadas sobre ~10 obras (single-digit ms no banco).
>
> **Baseline definitivo (200 usuários, P95 < 1.5s) exige load generator + app +
> banco co-localizados na mesma região** (ex.: app no Fly.io + Supabase + Locust
> na mesma região), onde o piso de rede some. Rodar dessa forma e colar os
> números aqui é o passo que fecha o critério de aceite na infra provisionada.

## Ponto de atenção sob carga

Atrás do pooler usamos `NullPool` (uma conexão por uso), delegando o pool ao
Supavisor. Com 200 usuários isso pressiona o limite de clientes do pooler —
monitorar saturação de conexões no New Relic durante o teste (é o mesmo eixo que
causou o hang da suíte antes do NullPool; agora o gargalo, se houver, é o pooler,
não o app).
