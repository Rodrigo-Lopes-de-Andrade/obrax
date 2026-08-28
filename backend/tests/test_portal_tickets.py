"""US-19 — chamados da obra no portal do cliente: leitura + resposta.

O cliente se autentica pelo token do portal no path (escopo = 1 obra), não por
JWT de acesso. Mensagens do cliente ficam com `author_id` NULL — é assim que o
chat distingue autoria sem inventar um `user` para o cliente.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.core.security import create_portal_token
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _seed_cliente(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente Beta"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _seed_obra(
    client: TestClient,
    owner: SeededUser,
    *,
    cliente_id: str | None = None,
    codigo: str = "OBR-1",
) -> str:
    # `documento` é único por tenant: duas obras do mesmo tenant reaproveitam o
    # cliente em vez de tentar cadastrá-lo de novo (409).
    cliente_id = cliente_id or _seed_cliente(client, owner)
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente_id, "codigo": codigo, "nome": "Residencial Jardim"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _seed_ticket(client: TestClient, owner: SeededUser, obra_id: str, *, titulo: str) -> str:
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": titulo, "descricao": "Detalhe do chamado"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _mint(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    resp = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["token"])


def test_cliente_le_chamados_com_historico(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ticket_id = _seed_ticket(client, owner, obra_id, titulo="Infiltração na laje")
    client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "Equipe a caminho."},
    )

    token = _mint(client, owner, obra_id)
    resp = client.get(f"/api/v1/portal/tickets/{token}")

    assert resp.status_code == 200, resp.text
    tickets = resp.json()
    assert len(tickets) == 1
    assert tickets[0]["titulo"] == "Infiltração na laje"
    assert tickets[0]["status"] == "aberto"
    mensagens = tickets[0]["mensagens"]
    assert [m["content"] for m in mensagens] == ["Equipe a caminho."]
    assert mensagens[0]["author_id"] == owner.user_id


def test_cliente_responde_chamado(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ticket_id = _seed_ticket(client, owner, obra_id, titulo="Prazo da fachada")
    token = _mint(client, owner, obra_id)

    resp = client.post(
        f"/api/v1/portal/tickets/{token}/{ticket_id}/mensagens",
        json={"content": "Podem começar na segunda."},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["content"] == "Podem começar na segunda."
    # author_id NULL = mensagem do cliente (não é um `user` do tenant).
    assert body["author_id"] is None
    assert body["attachment_paths"] == []

    # E aparece no histórico, em ordem cronológica.
    tickets = client.get(f"/api/v1/portal/tickets/{token}").json()
    assert [m["content"] for m in tickets[0]["mensagens"]] == ["Podem começar na segunda."]


def test_ticket_de_outra_obra_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    """O token do portal tem escopo de uma obra só: responder num chamado de
    outra obra do mesmo tenant não pode passar."""
    owner = seed_tenant(role="owner")
    cliente_id = _seed_cliente(client, owner)
    obra_a = _seed_obra(client, owner, cliente_id=cliente_id, codigo="OBR-A")
    obra_b = _seed_obra(client, owner, cliente_id=cliente_id, codigo="OBR-B")
    ticket_b = _seed_ticket(client, owner, obra_b, titulo="Chamado da obra B")
    token_a = _mint(client, owner, obra_a)

    resp = client.post(
        f"/api/v1/portal/tickets/{token_a}/{ticket_b}/mensagens",
        json={"content": "não deveria entrar"},
    )

    assert resp.status_code == 404


def test_chamado_de_outro_tenant_nao_vaza(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Token forjado com company_id de A e obra_id de B: a RLS (app.company_id = A)
    esconde os chamados de B — lista vazia, não os dados do outro tenant."""
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    _seed_ticket(client, owner_b, obra_b, titulo="Segredo do tenant B")

    forjado = create_portal_token(
        company_id=uuid.uuid4(),
        obra_id=uuid.UUID(obra_b),
        cliente_id=None,
    ).token

    assert client.get(f"/api/v1/portal/tickets/{forjado}").json() == []


def test_token_invalido_401(client: TestClient) -> None:
    assert client.get("/api/v1/portal/tickets/nao-e-um-jwt").status_code == 401


def test_mensagem_vazia_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ticket_id = _seed_ticket(client, owner, obra_id, titulo="Chamado")
    token = _mint(client, owner, obra_id)

    resp = client.post(
        f"/api/v1/portal/tickets/{token}/{ticket_id}/mensagens", json={"content": ""}
    )

    assert resp.status_code == 422


def test_ticket_soft_deletado_some_do_portal(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    ticket_id = _seed_ticket(client, owner, obra_id, titulo="Será removido")
    with SessionLocal() as s:
        s.execute(text("UPDATE ticket SET deleted_at = now() WHERE id = :id"), {"id": ticket_id})
        s.commit()

    token = _mint(client, owner, obra_id)

    assert client.get(f"/api/v1/portal/tickets/{token}").json() == []
