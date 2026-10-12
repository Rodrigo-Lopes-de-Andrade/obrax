"""B8.5 — health check com storage + realtime status.

`GET /health` é público (sem tenant) e reporta conectividade do object store e
o status do realtime. Em dev/CI o MinIO está de pé (docker-compose), então
`storage` deve ser "ok"; o realtime fica "disabled" (sem Supabase configurado).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


def test_health_reporta_storage_e_realtime(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # Postgres do compose de pé → os dois roles conectam.
    assert body["database"] == "ok"
    assert body["database_admin"] == "ok"
    # MinIO local de pé → storage acessível.
    assert body["storage"] == "ok"
    # Sem REALTIME_ENABLED + SUPABASE_* no ambiente de teste.
    assert body["realtime"] == "disabled"


def test_health_degraded_quando_role_admin_nao_conecta(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regressão: DSN do app_admin errado em prod derrubava o login com 500
    # enquanto o /health seguia "ok" e o smoke test passava.
    monkeypatch.setattr("app.main.db_healthy", lambda: {"app_user": True, "app_admin": False})
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["database"] == "ok"
    assert body["database_admin"] == "error"
