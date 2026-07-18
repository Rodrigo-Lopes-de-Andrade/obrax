"""O11.2 — dashboard de monitoring New Relic as-code (idempotente, via NerdGraph).

Pareia com `setup_nr_alerts.py` (B11.3): os alertas disparam, este painel mostra
o porquê. Constrói um dashboard sobre a telemetria OTLP que o backend já emite
(ver `app.core.observability`): spans HTTP (`Span`) e logs estruturados (`Log`).
Cria/atualiza de forma idempotente — buscar pelo nome, `dashboardUpdate` se já
existe, `dashboardCreate` se não; rodar de novo converge para o mesmo estado.

Só os widgets ancorados em telemetria real entram aqui. Fila de agentes, custo
de LLM, cache hit e pool de conexões do DB (O11.2 pede os 5) exigem métricas
custom que ainda não são emitidas — ficam de fora até existirem, mesma regra do
script de alertas. Os spans `client` (DB via SQLAlchemy, HTTP de saída) já são
capturados e entram no painel de chamadas de saída.

Uso:
    # imprime os widgets/NRQL p/ colar no query builder e validar (default):
    cd backend && uv run python -m scripts.setup_nr_dashboards

    # aplica de fato (cria/atualiza o dashboard):
    cd backend && uv run python -m scripts.setup_nr_dashboards --apply

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
from dataclasses import dataclass, field
from typing import Any

import httpx

DASHBOARD_NAME = "Obrax API — SLO"
DASHBOARD_DESCRIPTION = (
    "Observabilidade da API Obrax (O11.2) sobre telemetria OTLP real (Span/Log). "
    "Pareia com a policy de alertas 'Obrax API — SLO' (B11.3, RUNBOOK §4)."
)
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "obrax-api")

_ENDPOINTS = {
    "US": "https://api.newrelic.com/graphql",
    "EU": "https://api.eu.newrelic.com/graphql",
}

# Filtros reutilizados. Nomes de atributo validados contra a conta real (mesmos
# do setup_nr_alerts): Span tem `service.name`, `span.kind`, `http.status_code`,
# `duration.ms`, `name`; Log usa `severity.text`.
_SRV = f"service.name = '{SERVICE_NAME}'"
_SERVER = f"{_SRV} AND span.kind = 'server'"


@dataclass(frozen=True)
class Widget:
    """Um widget NRQL. `viz` é o id de visualização (viz.billboard/line/area/bar);
    `col`/`row`/`w`/`h` posicionam no grid de 12 colunas. `thresholds` (só faz
    sentido em billboard) é uma lista de (severidade, valor)."""

    title: str
    viz: str
    nrql: str
    col: int
    row: int
    w: int
    h: int
    thresholds: tuple[tuple[str, float], ...] = field(default=())


# Grid de 12 colunas. Linha 1: billboards de estado atual; linhas seguintes:
# séries temporais e facets para investigar.
WIDGETS: tuple[Widget, ...] = (
    Widget(
        title="Throughput (req/min)",
        viz="viz.billboard",
        nrql=f"SELECT rate(count(*), 1 minute) AS 'req/min' FROM Span WHERE {_SERVER}",
        col=1,
        row=1,
        w=3,
        h=3,
    ),
    Widget(
        title="Erro 5xx (%)",
        viz="viz.billboard",
        nrql=(
            "SELECT percentage(count(*), WHERE numeric(http.status_code) >= 500) AS '5xx %' "
            f"FROM Span WHERE {_SERVER}"
        ),
        col=4,
        row=1,
        w=3,
        h=3,
        thresholds=(("WARNING", 0.5), ("CRITICAL", 1.0)),
    ),
    Widget(
        title="Latência P95 (ms)",
        viz="viz.billboard",
        nrql=f"SELECT percentile(duration.ms, 95) FROM Span WHERE {_SERVER}",
        col=7,
        row=1,
        w=3,
        h=3,
        thresholds=(("WARNING", 500.0), ("CRITICAL", 1000.0)),
    ),
    Widget(
        title="Logs ERROR (últ. hora)",
        viz="viz.billboard",
        nrql=f"SELECT count(*) FROM Log WHERE {_SRV} AND severity.text = 'ERROR'",
        col=10,
        row=1,
        w=3,
        h=3,
        thresholds=(("WARNING", 1.0), ("CRITICAL", 10.0)),
    ),
    Widget(
        title="Latência de request (P50/P95/P99)",
        viz="viz.line",
        nrql=f"SELECT percentile(duration.ms, 50, 95, 99) FROM Span WHERE {_SERVER} TIMESERIES",
        col=1,
        row=4,
        w=6,
        h=3,
    ),
    Widget(
        title="Requests por classe de status",
        viz="viz.line",
        nrql=(
            "SELECT count(*) FROM Span WHERE "
            f"{_SERVER} FACET cases("
            "WHERE numeric(http.status_code) < 400 AS 'ok', "
            "WHERE numeric(http.status_code) >= 400 AND numeric(http.status_code) < 500 AS '4xx', "
            "WHERE numeric(http.status_code) >= 500 AS '5xx') TIMESERIES"
        ),
        col=7,
        row=4,
        w=6,
        h=3,
    ),
    Widget(
        title="Endpoints mais lentos (P95)",
        viz="viz.bar",
        nrql=f"SELECT percentile(duration.ms, 95) FROM Span WHERE {_SERVER} FACET name LIMIT 10",
        col=1,
        row=7,
        w=6,
        h=3,
    ),
    Widget(
        title="Logs ERROR no tempo",
        viz="viz.line",
        nrql=f"SELECT count(*) FROM Log WHERE {_SRV} AND severity.text = 'ERROR' TIMESERIES",
        col=7,
        row=7,
        w=6,
        h=3,
    ),
    Widget(
        title="Volume de logs por severidade",
        viz="viz.area",
        nrql=f"SELECT count(*) FROM Log WHERE {_SRV} FACET severity.text TIMESERIES",
        col=1,
        row=10,
        w=6,
        h=3,
    ),
    Widget(
        title="Chamadas de saída — DB/HTTP (P95)",
        viz="viz.line",
        nrql=(
            "SELECT percentile(duration.ms, 95) FROM Span WHERE "
            f"{_SRV} AND span.kind = 'client' TIMESERIES"
        ),
        col=7,
        row=10,
        w=6,
        h=3,
    ),
)


# ── NerdGraph ────────────────────────────────────────────────────────────────
_DASHBOARD_SEARCH = """
query($query: String!) {
  actor { entitySearch(query: $query) {
    results { entities { guid name } }
  } }
}
"""

_DASHBOARD_CREATE = """
mutation($accountId: Int!, $dashboard: DashboardInput!) {
  dashboardCreate(accountId: $accountId, dashboard: $dashboard) {
    entityResult { guid }
    errors { description type }
  }
}
"""

_DASHBOARD_UPDATE = """
mutation($guid: EntityGuid!, $dashboard: DashboardInput!) {
  dashboardUpdate(guid: $guid, dashboard: $dashboard) {
    entityResult { guid }
    errors { description type }
  }
}
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


def _raw_configuration(widget: Widget, account_id: int) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "nrqlQueries": [{"accountIds": [account_id], "query": widget.nrql}],
        "platformOptions": {"ignoreTimeRange": False},
    }
    if widget.thresholds:
        raw["thresholds"] = [{"alertSeverity": sev, "value": val} for sev, val in widget.thresholds]
    return raw


def _dashboard_input(account_id: int) -> dict[str, Any]:
    return {
        "name": DASHBOARD_NAME,
        "description": DASHBOARD_DESCRIPTION,
        "permissions": "PUBLIC_READ_WRITE",
        "pages": [
            {
                "name": "Visão geral",
                "description": "SLO e telemetria OTLP da API.",
                "widgets": [
                    {
                        "title": w.title,
                        "visualization": {"id": w.viz},
                        "layout": {"column": w.col, "row": w.row, "width": w.w, "height": w.h},
                        "rawConfiguration": _raw_configuration(w, account_id),
                    }
                    for w in WIDGETS
                ],
            }
        ],
    }


def _find_dashboard_guid(endpoint: str, api_key: str) -> str | None:
    query = f"name = '{DASHBOARD_NAME}' AND type = 'DASHBOARD'"
    data = _query(endpoint, api_key, _DASHBOARD_SEARCH, {"query": query})
    entities = data["actor"]["entitySearch"]["results"]["entities"]
    for ent in entities:
        if ent["name"] == DASHBOARD_NAME:
            return str(ent["guid"])
    return None


def _apply(account_id: int) -> int:
    api_key = os.getenv("NEW_RELIC_API_KEY")
    if not api_key:
        print("NEW_RELIC_API_KEY não setada — necessária para --apply.", file=sys.stderr)
        return 1
    endpoint = _ENDPOINTS[os.getenv("NEW_RELIC_REGION", "US").upper()]

    dashboard = _dashboard_input(account_id)
    guid = _find_dashboard_guid(endpoint, api_key)

    if guid:
        data = _query(endpoint, api_key, _DASHBOARD_UPDATE, {"guid": guid, "dashboard": dashboard})
        result = data["dashboardUpdate"]
        verb = "atualizado"
    else:
        data = _query(
            endpoint, api_key, _DASHBOARD_CREATE, {"accountId": account_id, "dashboard": dashboard}
        )
        result = data["dashboardCreate"]
        verb = "criado"

    if result.get("errors"):
        print(f"Falha ao aplicar dashboard: {json.dumps(result['errors'])}", file=sys.stderr)
        return 1

    new_guid = result["entityResult"]["guid"]
    print(f"  dashboard '{DASHBOARD_NAME}' {verb} (guid={new_guid})")
    print(f"\n{len(WIDGETS)} widgets convergidos no dashboard '{DASHBOARD_NAME}'.")
    return 0


def _dry_run() -> int:
    print(f"[dry-run] dashboard '{DASHBOARD_NAME}' — {len(WIDGETS)} widgets:\n")
    for w in WIDGETS:
        viz = w.viz.removeprefix("viz.")
        print(f"● {w.title}  [{viz} @ col {w.col} row {w.row} {w.w}x{w.h}]")
        if w.thresholds:
            th = ", ".join(f"{sev.lower()} ≥ {val}" for sev, val in w.thresholds)
            print(f"    thresholds: {th}")
        print(f"    NRQL: {w.nrql}\n")
    print("Valide as NRQL no query builder do New Relic e rode com --apply para publicar.")
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
    parser = argparse.ArgumentParser(
        description="Publica o dashboard de monitoring da API Obrax (O11.2)."
    )
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
