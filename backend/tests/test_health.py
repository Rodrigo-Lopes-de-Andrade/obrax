"""B8.5 — health check com storage + realtime status.

`GET /health` é público (sem tenant) e reporta conectividade do object store e
o status do realtime. Em dev/CI o MinIO está de pé (docker-compose), então
`storage` deve ser "ok"; o realtime fica "disabled" (sem Supabase configurado).
"""

from __future__ import annotations

from starlette.testclient import TestClient


def test_health_reporta_storage_e_realtime(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # MinIO local de pé → storage acessível.
    assert body["storage"] == "ok"
    # Sem REALTIME_ENABLED + SUPABASE_* no ambiente de teste.
    assert body["realtime"] == "disabled"
