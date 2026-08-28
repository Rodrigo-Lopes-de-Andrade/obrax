"""Testes de API do Módulo 3 (Sprint 10) — EXIGEM Postgres (make test).

Cobrem o painel IA (permissões, assistente, auditoria/reverter, copilot,
insights, feature-flags) e o webhook Uazapi ponta a ponta (HMAC → idempotência →
fila), além do isolamento por tenant (RLS). Escritos no estilo de
test_tickets_crud.py (TestClient + fixture seed_tenant).

NB: não foram executados no ambiente de desenvolvimento sem banco; a lógica pura
(HMAC/fila/intent/copilot/métricas) é coberta e executada em test_agentes_unit.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest
from httpx import Response
from starlette.testclient import TestClient

from app.core.config import settings
from app.integrations.agent_queue import InProcessAgentQueue, get_agent_queue
from app.main import app
from app.modules.agentes import router as agentes_router
from tests.conftest import SeededUser

_SECRET = "webhook-test-secret"


def _perm_body(number: str, role: str = "solicitador") -> dict[str, object]:
    return {
        "whatsapp_number": number,
        "role": role,
        "daily_limit_cents": 0,
        "monthly_limit_cents": 0,
    }


class TestPermissoes:
    def test_crud_e_upsert(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        owner = seed_tenant(role="owner")
        # cria
        r = client.post(
            "/api/v1/ia/permissoes", json=_perm_body("+5511999990000"), headers=owner.auth_header
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        # upsert: mesmo número muda o papel, não duplica
        r2 = client.post(
            "/api/v1/ia/permissoes",
            json=_perm_body("+5511999990000", role="aprovador"),
            headers=owner.auth_header,
        )
        assert r2.status_code == 201
        listed = client.get("/api/v1/ia/permissoes", headers=owner.auth_header).json()
        assert len(listed["items"]) == 1
        assert listed["items"][0]["role"] == "aprovador"
        # remove
        assert (
            client.delete(f"/api/v1/ia/permissoes/{pid}", headers=owner.auth_header).status_code
            == 204
        )

    def test_delete_inexistente_404(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        owner = seed_tenant(role="owner")
        r = client.delete(
            "/api/v1/ia/permissoes/00000000-0000-0000-0000-000000000000",
            headers=owner.auth_header,
        )
        assert r.status_code == 404

    def test_criar_exige_owner_admin(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        gestor = seed_tenant(role="gestor")
        r = client.post(
            "/api/v1/ia/permissoes", json=_perm_body("+5511900000000"), headers=gestor.auth_header
        )
        assert r.status_code == 403


class TestAssistente:
    def test_envia_e_reconstroi_thread(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        user = seed_tenant(role="owner")
        r = client.post(
            "/api/v1/ia/assistente/mensagens",
            json={"content": "Qual o status da obra?"},
            headers=user.auth_header,
        )
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "assistant"
        thread = client.get("/api/v1/ia/assistente/mensagens", headers=user.auth_header).json()
        assert [m["role"] for m in thread] == ["user", "assistant"]


class TestAuditoria:
    def test_consulta_nao_reversivel(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        user = seed_tenant(role="owner")
        client.post(
            "/api/v1/ia/assistente/mensagens",
            json={"content": "status da obra"},
            headers=user.auth_header,
        )
        inter = client.get("/api/v1/ia/interacoes", headers=user.auth_header).json()
        assert len(inter["items"]) == 1
        interaction_id = inter["items"][0]["id"]
        # consulta (action=None) → 409 ao tentar reverter
        r = client.post(
            f"/api/v1/ia/interacoes/{interaction_id}/reverter", headers=user.auth_header
        )
        assert r.status_code == 409

    def test_compra_via_painel_e_reversivel(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        user = seed_tenant(role="owner")
        client.post(
            "/api/v1/ia/assistente/mensagens",
            json={"content": "Solicitar 10 sacos de cimento"},
            headers=user.auth_header,
        )
        inter = client.get("/api/v1/ia/interacoes?agent=compras", headers=user.auth_header).json()
        assert len(inter["items"]) == 1
        rid = inter["items"][0]["id"]
        r = client.post(f"/api/v1/ia/interacoes/{rid}/reverter", headers=user.auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "revertido"
        # dupla reversão → 409
        assert (
            client.post(
                f"/api/v1/ia/interacoes/{rid}/reverter", headers=user.auth_header
            ).status_code
            == 409
        )


class TestCopilotEInsights:
    def test_copilot(self, client: TestClient, seed_tenant: Callable[..., SeededUser]) -> None:
        user = seed_tenant()
        r = client.post(
            "/api/v1/ia/copilot/sugerir",
            json={"descricao": "alvenaria"},
            headers=user.auth_header,
        )
        assert r.status_code == 200
        assert any("Bloco" in i["descricao"] for i in r.json())

    def test_feature_flag_ligada(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        user = seed_tenant()
        r = client.get("/api/v1/feature-flags", headers=user.auth_header)
        assert r.json()["ia-module-enabled"] is True


class TestRlsIsolamento:
    def test_permissao_nao_vaza_entre_tenants(
        self, client: TestClient, seed_tenant: Callable[..., SeededUser]
    ) -> None:
        a = seed_tenant(role="owner")
        b = seed_tenant(role="owner")
        client.post(
            "/api/v1/ia/permissoes", json=_perm_body("+5511911111111"), headers=a.auth_header
        )
        listed_b = client.get("/api/v1/ia/permissoes", headers=b.auth_header).json()
        assert listed_b["items"] == []


@pytest.fixture
def webhook_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[InProcessAgentQueue]:
    """Injeta um segredo de HMAC conhecido e uma fila limpa capturável."""
    queue = InProcessAgentQueue()
    monkeypatch.setattr(
        agentes_router, "settings", replace(settings, uazapi_webhook_secret=_SECRET)
    )
    app.dependency_overrides[get_agent_queue] = lambda: queue
    yield queue
    app.dependency_overrides.pop(get_agent_queue, None)


class TestWebhook:
    def _post(self, client: TestClient, body: dict[str, str]) -> Response:
        raw = json.dumps(body).encode()
        sig = hmac.new(_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        return client.post(
            "/api/v1/webhook/uazapi",
            content=raw,
            headers={"content-type": "application/json", "x-uazapi-signature": sig},
        )

    def test_assinatura_invalida_401(
        self, client: TestClient, webhook_env: InProcessAgentQueue
    ) -> None:
        r = client.post(
            "/api/v1/webhook/uazapi",
            content=b'{"message_id":"1","from_number":"+551199","text":"oi"}',
            headers={"content-type": "application/json", "x-uazapi-signature": "errado"},
        )
        assert r.status_code == 401

    def test_numero_desconhecido_ignored(
        self, client: TestClient, webhook_env: InProcessAgentQueue
    ) -> None:
        r = self._post(
            client, {"message_id": "m1", "from_number": "+5511900000000", "text": "status"}
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"
        assert len(webhook_env) == 0

    def test_enfileira_e_idempotente(
        self,
        client: TestClient,
        seed_tenant: Callable[..., SeededUser],
        webhook_env: InProcessAgentQueue,
    ) -> None:
        owner = seed_tenant(role="owner")
        client.post(
            "/api/v1/ia/permissoes", json=_perm_body("+5511922223333"), headers=owner.auth_header
        )
        body = {"message_id": "wamid-1", "from_number": "+5511922223333", "text": "status"}
        first = self._post(client, body)
        assert first.json()["status"] == "queued"
        assert len(webhook_env) == 1
        # reentrega do mesmo message_id não duplica
        second = self._post(client, body)
        assert second.json()["status"] == "duplicate"
        assert len(webhook_env) == 1
