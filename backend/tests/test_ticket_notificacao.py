"""B4.5 — notificação por e-mail ao abrir um chamado (US-08 / US-20 prep).

Contrato em docs/SPRINTS.md B4.5: ao criar ticket, owners/admins do tenant
recebem um aviso com título/descrição/obra. O notifier é substituído por um
fake gravador via `dependency_overrides` (dev/CI não enviam e-mail) — ver
app/integrations/notifications.py.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.integrations.notifications import EmailMessage, get_notifier
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class ExplodingNotifier:
    def send(self, message: EmailMessage) -> None:
        raise RuntimeError("provedor de e-mail fora do ar")


@pytest.fixture
def notifier() -> Iterator[RecordingNotifier]:
    rec = RecordingNotifier()
    app.dependency_overrides[get_notifier] = lambda: rec
    yield rec
    app.dependency_overrides.pop(get_notifier, None)


@pytest.fixture
def with_exploding_notifier() -> Iterator[None]:
    app.dependency_overrides[get_notifier] = ExplodingNotifier
    yield
    app.dependency_overrides.pop(get_notifier, None)


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    cliente = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    ).json()
    return str(
        client.post(
            "/api/v1/obras",
            headers=owner.auth_header,
            json={"cliente_id": cliente["id"], "codigo": "OBR-1", "nome": "Reforma"},
        ).json()["id"]
    )


@pytest.fixture
def add_tenant_user() -> Iterator[Callable[..., str]]:
    """Fábrica: adiciona um usuário com `role` a um tenant (via `obrax`, bypassa
    RLS) e devolve o e-mail (único). Remove os usuários criados no teardown —
    `users` é identidade global e não cascateia com a company."""
    created: list[str] = []

    def _add(company_id: str, *, role: str) -> str:
        email = f"extra-{secrets.token_hex(6)}@ex.com"
        with SessionLocal() as session:
            uid = session.execute(
                text(
                    "INSERT INTO users (email, password_hash, nome) "
                    "VALUES (:email, :ph, 'Extra') RETURNING id"
                ),
                {"email": email, "ph": hash_password("x")},
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO user_company_role (company_id, user_id, role) "
                    "VALUES (:cid, :uid, CAST(:role AS user_role))"
                ),
                {"cid": company_id, "uid": uid, "role": role},
            )
            session.commit()
        created.append(str(uid))
        return email

    yield _add

    with SessionLocal() as session:
        for uid in created:
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        session.commit()


def test_ticket_criado_notifica_admin(
    client: TestClient, seed_tenant: SeedTenant, notifier: RecordingNotifier
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": "Vazamento", "descricao": "Infiltração na laje."},
    )
    assert resp.status_code == 201, resp.text

    assert len(notifier.sent) == 1
    msg = notifier.sent[0]
    assert owner.email in msg.to
    assert "Vazamento" in msg.subject
    assert "Infiltração na laje." in msg.body
    assert msg.template == "ticket_created"
    assert msg.context["obra_id"] == obra_id
    assert msg.context["titulo"] == "Vazamento"


def test_notifica_admins_nao_viewers_do_tenant(
    client: TestClient,
    seed_tenant: SeedTenant,
    notifier: RecordingNotifier,
    add_tenant_user: Callable[..., str],
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    admin2 = add_tenant_user(owner.company_id, role="admin")
    add_tenant_user(owner.company_id, role="viewer")

    client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": "X"},
    )
    to = set(notifier.sent[0].to)
    assert to == {owner.email, admin2}  # viewer fica de fora


def test_notificacao_isolada_por_tenant(
    client: TestClient, seed_tenant: SeedTenant, notifier: RecordingNotifier
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_a = _seed_obra(client, owner_a)

    client.post(
        f"/api/v1/obras/{obra_a}/tickets", headers=owner_a.auth_header, json={"titulo": "A"}
    )
    # Só o admin do tenant A é avisado; o de B (outro tenant) não aparece.
    assert set(notifier.sent[0].to) == {owner_a.email}
    assert owner_b.email not in notifier.sent[0].to


def test_notify_falha_nao_quebra(
    client: TestClient, seed_tenant: SeedTenant, with_exploding_notifier: None
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/tickets",
        headers=owner.auth_header,
        json={"titulo": "sobrevive"},
    )
    # Notifier explode, mas o chamado foi criado e o request respondeu 201.
    assert resp.status_code == 201
    assert resp.json()["titulo"] == "sobrevive"
