"""B11.3 — alertas New Relic as-code (idempotente, via NerdGraph).

Define as condições de alerta sobre a telemetria OTLP que o backend já emite
(ver `app.core.observability`): spans de HTTP (`Span`) e logs estruturados
(`Log`). Cria/atualiza uma policy e suas condições NRQL de forma idempotente —
rodar de novo converge para o mesmo estado, não duplica.

Só as condições ancoradas em telemetria real entram aqui. Fila de agentes,
saúde de LLM/Uazapi e CPU do host (RUNBOOK §4) exigem métricas custom ou o
New Relic infra-agent, que ainda não existem — ficam de fora até serem emitidas.

Uso:
    # imprime as NRQL/thresholds p/ colar no query builder e validar (default):
    cd backend && uv run python -m scripts.setup_nr_alerts

    # aplica de fato (cria/atualiza a policy + condições):
    cd backend && uv run python -m scripts.setup_nr_alerts --apply

Env (lidas do .env da raiz no --apply, ou do ambiente):
    NEW_RELIC_API_KEY      User key (NRAK-...) — obrigatória só no --apply.
    NEW_RELIC_ACCOUNT_ID   ID numérico da conta — obrigatória só no --apply.
    NEW_RELIC_REGION       US (default) | EU — escolhe o endpoint NerdGraph.
    OTEL_SERVICE_NAME      Nome do serviço nos filtros NRQL (default obrax-api).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx

POLICY_NAME = "Obrax API — SLO"
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "obrax-api")

_ENDPOINTS = {
    "US": "https://api.newrelic.com/graphql",
    "EU": "https://api.eu.newrelic.com/graphql",
}


@dataclass(frozen=True)
class Condition:
    """Uma condição NRQL estática. `threshold`/`operator` viram um único term
    CRITICAL; `duration_s` é a janela em que a violação precisa persistir."""

    name: str
    nrql: str
    operator: str  # ABOVE | BELOW
    threshold: float
    duration_s: int
    description: str


# Ancoradas na telemetria emitida hoje. Nomes de atributo validados contra a
# conta real (NerdGraph keyset): Span tem `http.status_code`, `duration.ms` e
# `span.kind`; Log usa `severity.text` (INFO/ERROR/…), não `level`.
CONDITIONS: tuple[Condition, ...] = (
    Condition(
        name="5xx > 1% (5 min)",
        nrql=(
            "SELECT percentage(count(*), WHERE numeric(http.status_code) >= 500) "
            f"FROM Span WHERE service.name = '{SERVICE_NAME}' AND span.kind = 'server'"
        ),
        operator="ABOVE",
        threshold=1.0,
        duration_s=300,
        description="Taxa de resposta 5xx acima de 1% por 5 min (RUNBOOK §4).",
    ),
    Condition(
        name="Latência P95 > 1s (5 min)",
        nrql=(
            "SELECT percentile(duration.ms, 95) "
            f"FROM Span WHERE service.name = '{SERVICE_NAME}' AND span.kind = 'server'"
        ),
        operator="ABOVE",
        threshold=1000.0,
        duration_s=300,
        description="P95 de latência de request acima de 1s. Threshold tunável.",
    ),
    Condition(
        name="Logs ERROR em alta (5 min)",
        nrql=(
            "SELECT count(*) FROM Log "
            f"WHERE service.name = '{SERVICE_NAME}' AND severity.text = 'ERROR'"
        ),
        operator="ABOVE",
        threshold=10.0,
        duration_s=300,
        description="Mais de 10 logs de nível ERROR em 5 min. Threshold tunável.",
    ),
    Condition(
        name="Sem telemetria (app down, 5 min)",
        nrql=(f"SELECT count(*) FROM Span WHERE service.name = '{SERVICE_NAME}'"),
        operator="BELOW",
        threshold=1.0,
        duration_s=300,
        description="Nenhum span em 5 min — proxy de serviço fora do ar.",
    ),
)


# ── NerdGraph ────────────────────────────────────────────────────────────────
_POLICY_SEARCH = """
query($accountId: Int!, $name: String!) {
  actor { account(id: $accountId) { alerts {
    policiesSearch(searchCriteria: {name: $name}) { policies { id name } }
  } } }
}
"""

_POLICY_CREATE = """
mutation($accountId: Int!, $name: String!) {
  alertsPolicyCreate(accountId: $accountId,
    policy: {name: $name, incidentPreference: PER_CONDITION}) { id }
}
"""

_CONDITIONS_SEARCH = """
query($accountId: Int!, $policyId: String!) {
  actor { account(id: $accountId) { alerts {
    nrqlConditionsSearch(searchCriteria: {policyId: $policyId}) {
      nrqlConditions { id name }
    }
  } } }
}
"""

_CONDITION_INPUT = """
  name: $name, enabled: true,
  nrql: {query: $nrql},
  terms: {operator: $operator, threshold: $threshold, priority: CRITICAL,
          thresholdOccurrences: AT_LEAST_ONCE, thresholdDuration: $duration},
  signal: {aggregationMethod: EVENT_FLOW, aggregationWindow: 60, aggregationDelay: 120},
  violationTimeLimitSeconds: 259200
"""

_CONDITION_CREATE = f"""
mutation($accountId: Int!, $policyId: ID!, $name: String!, $nrql: String!,
         $operator: AlertsNrqlConditionTermsOperator!, $threshold: Float!, $duration: Seconds!) {{
  alertsNrqlConditionStaticCreate(accountId: $accountId, policyId: $policyId,
    condition: {{{_CONDITION_INPUT}}}) {{ id }}
}}
"""

_CONDITION_UPDATE = f"""
mutation($accountId: Int!, $id: ID!, $name: String!, $nrql: String!,
         $operator: AlertsNrqlConditionTermsOperator!, $threshold: Float!, $duration: Seconds!) {{
  alertsNrqlConditionStaticUpdate(accountId: $accountId, id: $id,
    condition: {{{_CONDITION_INPUT}}}) {{ id }}
}}
"""


def _query(endpoint: str, api_key: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resp = httpx.post(
        endpoint,
        headers={"API-Key": api_key, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=30.0,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(f"NerdGraph error: {json.dumps(body['errors'])}")
    data: dict[str, Any] = body["data"]
    return data


def _ensure_policy(endpoint: str, api_key: str, account_id: int) -> str:
    data = _query(endpoint, api_key, _POLICY_SEARCH, {"accountId": account_id, "name": POLICY_NAME})
    found = data["actor"]["account"]["alerts"]["policiesSearch"]["policies"]
    if found:
        print(f"  policy '{POLICY_NAME}' já existe (id={found[0]['id']})")
        return str(found[0]["id"])
    data = _query(endpoint, api_key, _POLICY_CREATE, {"accountId": account_id, "name": POLICY_NAME})
    policy_id = str(data["alertsPolicyCreate"]["id"])
    print(f"  policy '{POLICY_NAME}' criada (id={policy_id})")
    return policy_id


def _apply(account_id: int) -> int:
    api_key = os.getenv("NEW_RELIC_API_KEY")
    if not api_key:
        print("NEW_RELIC_API_KEY não setada — necessária para --apply.", file=sys.stderr)
        return 1
    endpoint = _ENDPOINTS[os.getenv("NEW_RELIC_REGION", "US").upper()]

    policy_id = _ensure_policy(endpoint, api_key, account_id)
    existing = _query(
        endpoint, api_key, _CONDITIONS_SEARCH, {"accountId": account_id, "policyId": policy_id}
    )
    by_name = {
        c["name"]: c["id"]
        for c in existing["actor"]["account"]["alerts"]["nrqlConditionsSearch"]["nrqlConditions"]
    }

    for cond in CONDITIONS:
        shared = {
            "accountId": account_id,
            "name": cond.name,
            "nrql": cond.nrql,
            "operator": cond.operator,
            "threshold": cond.threshold,
            "duration": cond.duration_s,
        }
        if cond.name in by_name:
            _query(endpoint, api_key, _CONDITION_UPDATE, {**shared, "id": by_name[cond.name]})
            print(f"  ~ atualizada: {cond.name}")
        else:
            _query(endpoint, api_key, _CONDITION_CREATE, {**shared, "policyId": policy_id})
            print(f"  + criada:     {cond.name}")
    print(f"\n{len(CONDITIONS)} condições convergidas na policy '{POLICY_NAME}'.")
    return 0


def _dry_run() -> int:
    print(f"[dry-run] policy '{POLICY_NAME}' — {len(CONDITIONS)} condições:\n")
    for cond in CONDITIONS:
        op = "acima de" if cond.operator == "ABOVE" else "abaixo de"
        print(f"● {cond.name}")
        print(f"    {cond.description}")
        print(f"    dispara: {op} {cond.threshold} por {cond.duration_s // 60} min")
        print(f"    NRQL: {cond.nrql}\n")
    print("Valide as NRQL no query builder do New Relic e rode com --apply para armar.")
    return 0


def _load_env() -> None:
    """Carrega as NEW_RELIC_* do .env da raiz do repo (sem sobrescrever o que
    já estiver no ambiente), para o --apply rodar sem prefixo de export."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Arma os alertas New Relic da API Obrax (B11.3).")
    parser.add_argument("--apply", action="store_true", help="Aplica de fato (default: dry-run).")
    args = parser.parse_args(argv)

    if not args.apply:
        return _dry_run()

    _load_env()

    account_raw = os.getenv("NEW_RELIC_ACCOUNT_ID")
    if not account_raw or not account_raw.isdigit():
        print(
            "NEW_RELIC_ACCOUNT_ID (numérico) não setada — necessária para --apply.", file=sys.stderr
        )
        return 1
    return _apply(int(account_raw))


if __name__ == "__main__":
    raise SystemExit(main())
