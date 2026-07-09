"""B4.3 — mensagens (chat) do ticket + evento de realtime (US-08).

Contrato em docs/ESPEC.md § 6 / docs/SPRINTS.md B4.3: POST/GET mensagens (texto
+ até 5 anexos) e, ao gravar, um evento no canal do ticket. O publisher é
substituído por um fake gravador via `dependency_overrides` (dev/CI não têm
Supabase) — ver app/integrations/events.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.integrations.events import DomainEvent, get_event_publisher
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


class RecordingPublisher:
    """Fake que grava os eventos publicados, para asserção nos testes."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


class ExplodingPublisher:
    """Fake que sempre falha — prova que o realtime é best-effort."""

    def publish(self, event: DomainEvent) -> None:
        raise RuntimeError("supabase indisponível")


@pytest.fixture
def recorder() -> Iterator[RecordingPublisher]:
    rec = RecordingPublisher()
    app.dependency_overrides[get_event_publisher] = lambda: rec
    yield rec
    app.dependency_overrides.pop(get_event_publisher, None)


@pytest.fixture
def with_exploding_publisher() -> Iterator[None]:
    app.dependency_overrides[get_event_publisher] = ExplodingPublisher
    yield
    app.dependency_overrides.pop(get_event_publisher, None)


def _seed_ticket(client: TestClient, owner: SeededUser) -> str:
    cliente = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    ).json()
    obra_id = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente["id"], "codigo": "OBR-1", "nome": "Reforma"},
    ).json()["id"]
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": "Vazamento no 3º andar"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _post_msg(client: TestClient, owner: SeededUser, ticket_id: str, **over: object) -> dict:
    body: dict = {"content": "Bom dia, alguma novidade?"}
    body.update(over)
    return client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens", headers=owner.auth_header, json=body
    ).json()


def test_post_e_list_mensagem(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)

    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "Equipe a caminho.", "attachment_paths": ["co/ob/foto.jpg"]},
    )
    assert resp.status_code == 201, resp.text
    msg = resp.json()
    assert msg["ticket_id"] == ticket_id
    assert msg["author_id"] == owner.user_id
    assert msg["content"] == "Equipe a caminho."
    assert msg["attachment_paths"] == ["co/ob/foto.jpg"]

    page = client.get(f"/api/v1/tickets/{ticket_id}/mensagens", headers=owner.auth_header).json()
    assert [m["id"] for m in page["items"]] == [msg["id"]]
    assert page["next_cursor"] is None


def test_content_vazio_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": ""},
    )
    assert resp.status_code == 422


def test_content_grande_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "a" * 5001},
    )
    assert resp.status_code == 422


def test_cinco_anexos_ok(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    paths = [f"co/ob/f{i}.jpg" for i in range(5)]
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "5 fotos", "attachment_paths": paths},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["attachment_paths"] == paths


def test_seis_anexos_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "6 fotos", "attachment_paths": [f"co/ob/f{i}.jpg" for i in range(6)]},
    )
    assert resp.status_code == 422


def test_anexo_url_rejeitada_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "link", "attachment_paths": ["https://cdn.exemplo/f.jpg"]},
    )
    assert resp.status_code == 422


def test_ticket_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    fake = uuid.uuid4()
    assert (
        client.post(
            f"/api/v1/tickets/{fake}/mensagens",
            headers=owner.auth_header,
            json={"content": "oi"},
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/tickets/{fake}/mensagens", headers=owner.auth_header).status_code
        == 404
    )


def test_cross_tenant_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    ticket_b = _seed_ticket(client, owner_b)
    _post_msg(client, owner_b, ticket_b)

    # Tenant A não enxerga o ticket de B (RLS) → 404 no post e no list.
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_b}/mensagens",
            headers=owner_a.auth_header,
            json={"content": "intruso"},
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/tickets/{ticket_b}/mensagens", headers=owner_a.auth_header).status_code
        == 404
    )


def test_viewer_pode_conversar(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Chat é aberto a qualquer usuário do tenant (o cliente também responde),
    como abrir chamado — não é escrita restrita a owner/admin/gestor. Mintamos um
    JWT com role `viewer` para o MESMO usuário/empresa (a RLS enxerga o ticket),
    provando que a rota não tem `require_roles`."""
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    viewer_token = create_access_token(
        user_id=uuid.UUID(owner.user_id),
        company_id=uuid.UUID(owner.company_id),
        role="viewer",
    ).token
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"content": "resposta do viewer"},
    )
    assert resp.status_code == 201


def test_paginacao_cursor(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    ids = [_post_msg(client, owner, ticket_id, content=f"msg {i}")["id"] for i in range(3)]

    p1 = client.get(
        f"/api/v1/tickets/{ticket_id}/mensagens?limit=2", headers=owner.auth_header
    ).json()
    # Mais recentes primeiro.
    assert [m["id"] for m in p1["items"]] == [ids[2], ids[1]]
    assert p1["next_cursor"] is not None

    p2 = client.get(
        f"/api/v1/tickets/{ticket_id}/mensagens?limit=2&cursor={p1['next_cursor']}",
        headers=owner.auth_header,
    ).json()
    assert [m["id"] for m in p2["items"]] == [ids[0]]
    assert p2["next_cursor"] is None


def test_evento_realtime_publicado(
    client: TestClient, seed_tenant: SeedTenant, recorder: RecordingPublisher
) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "olá realtime"},
    )
    assert resp.status_code == 201
    assert len(recorder.events) == 1
    ev = recorder.events[0]
    assert ev.channel == f"ticket:{ticket_id}"
    assert ev.event == "ticket.mensagem.created"
    assert ev.payload["content"] == "olá realtime"
    assert ev.payload["id"] == resp.json()["id"]


def test_publish_falha_nao_quebra(
    client: TestClient, seed_tenant: SeedTenant, with_exploding_publisher: None
) -> None:
    owner = seed_tenant(role="owner")
    ticket_id = _seed_ticket(client, owner)
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/mensagens",
        headers=owner.auth_header,
        json={"content": "sobrevive"},
    )
    # Publisher explode, mas a mensagem foi persistida e o request respondeu 201.
    assert resp.status_code == 201
    page = client.get(f"/api/v1/tickets/{ticket_id}/mensagens", headers=owner.auth_header).json()
    assert [m["content"] for m in page["items"]] == ["sobrevive"]
