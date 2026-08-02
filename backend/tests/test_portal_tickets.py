"""US-19 — portal do cliente: chamados (leitura) + responder mensagens.

O admin (owner) cria a obra, os chamados e as mensagens internas via API
autenticada; o cliente acessa pelo token do portal (path). Cobre o feliz
(listar com histórico + responder), o isolamento por obra (chamado de outra
obra → 404) e o chamado fechado (409).
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _seed_obra(client: TestClient, owner: SeededUser, *, codigo: str) -> str:
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente Beta"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": codigo, "nome": "Residencial Jardim"},
    ).json()
    return str(obra["id"])


def _criar_ticket(client: TestClient, owner: SeededUser, obra_id: str, *, titulo: str) -> str:
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": titulo},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _mint(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    resp = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["token"])


def test_listar_e_responder(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner, codigo="OBR-1")
    ticket_id = _criar_ticket(client, owner, obra_id, titulo="Vazamento no 3º andar")
    # Mensagem interna do gestor (author_id preenchido).
    client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "Equipe a caminho."},
    )

    token = _mint(client, owner, obra_id)

    lista = client.get(f"/api/v1/portal/tickets/{token}")
    assert lista.status_code == 200, lista.text
    tickets = lista.json()
    assert len(tickets) == 1
    t = tickets[0]
    assert t["titulo"] == "Vazamento no 3º andar"
    assert t["status"] == "aberto"
    assert len(t["mensagens"]) == 1
    assert t["mensagens"][0]["author_id"] is not None  # mensagem do gestor

    # Cliente responde: author_id NULL (a UI alinha à direita como "Você").
    resp = client.post(
        f"/api/v1/portal/tickets/{token}/{ticket_id}/mensagens",
        json={"content": "Obrigado, aguardo."},
    )
    assert resp.status_code == 201, resp.text
    msg = resp.json()
    assert msg["author_id"] is None
    assert msg["content"] == "Obrigado, aguardo."
    assert msg["ticket_id"] == ticket_id

    # Aparece no histórico, em ordem cronológica.
    de_novo = client.get(f"/api/v1/portal/tickets/{token}").json()[0]["mensagens"]
    assert [m["content"] for m in de_novo] == ["Equipe a caminho.", "Obrigado, aguardo."]


def test_responder_chamado_fechado_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner, codigo="OBR-1")
    ticket_id = _criar_ticket(client, owner, obra_id, titulo="Dúvida")
    client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        headers=owner.auth_header,
        json={"status": "fechado"},
    )

    token = _mint(client, owner, obra_id)
    resp = client.post(
        f"/api/v1/portal/tickets/{token}/{ticket_id}/mensagens",
        json={"content": "Ainda dá pra responder?"},
    )
    assert resp.status_code == 409, resp.text


def test_ticket_de_outra_obra_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Token da obra A não pode postar num chamado da obra B (mesmo tenant)."""
    owner = seed_tenant(role="owner")
    obra_a = _seed_obra(client, owner, codigo="OBR-A")
    obra_b_cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": "11444777000161", "nome": "Cliente B"},
    ).json()
    obra_b = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": obra_b_cli["id"], "codigo": "OBR-B", "nome": "Obra B"},
    ).json()["id"]
    ticket_b = _criar_ticket(client, owner, str(obra_b), titulo="Chamado da B")

    token_a = _mint(client, owner, obra_a)
    # Token da A só enxerga chamados da A.
    assert client.get(f"/api/v1/portal/tickets/{token_a}").json() == []
    resp = client.post(
        f"/api/v1/portal/tickets/{token_a}/{ticket_b}/mensagens",
        json={"content": "invasão"},
    )
    assert resp.status_code == 404, resp.text


def test_token_invalido_401(client: TestClient) -> None:
    assert client.get("/api/v1/portal/tickets/nao-e-um-jwt").status_code == 401
