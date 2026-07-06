"""B1.5 — convites de usuário (docs/SPRINTS.md, critério de aceite:
"Invite envia email, link 1x use, password setup 8 chars min").

Sem job de e-mail nesta sprint, o token do convite volta no corpo da resposta
(ver nota em app/modules/users/schemas.py) — é o que permite testar o fluxo
ponta a ponta aqui.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


@pytest.fixture
def cleanup_emails() -> Iterator[list[str]]:
    """Remove usuários criados por `accept-invite` (não são rastreados por
    `seed_tenant`, pois `users` não cascateia a partir de `companies`)."""
    emails: list[str] = []
    yield emails
    with SessionLocal() as session:
        for email in emails:
            session.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        session.commit()


def test_invite_convida_e_aceita_cria_usuario(
    client: TestClient, seed_tenant: SeedTenant, cleanup_emails: list[str]
) -> None:
    owner = seed_tenant(role="owner")
    invited_email = f"convidado-{secrets.token_hex(6)}@example.com"
    cleanup_emails.append(invited_email)

    invite = client.post(
        "/api/v1/users/invite",
        headers=owner.auth_header,
        json={"email": invited_email, "role": "gestor"},
    )
    assert invite.status_code == 201
    invite_body = invite.json()
    assert invite_body["role"] == "gestor"
    assert invite_body["invite_token"]

    listed = client.get("/api/v1/users/invite", headers=owner.auth_header)
    assert listed.status_code == 200
    assert any(item["email"] == invited_email for item in listed.json())

    accept = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": invite_body["invite_token"], "nome": "Convidado", "password": "senha12345"},
    )
    assert accept.status_code == 204

    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT ucr.company_id, ucr.role FROM users u "
                "JOIN user_company_role ucr ON ucr.user_id = u.id "
                "WHERE u.email = :email"
            ),
            {"email": invited_email},
        ).first()
    assert row is not None
    assert str(row[0]) == owner.company_id
    assert row[1] == "gestor"


def test_aceitar_convite_duas_vezes_falha_401(
    client: TestClient, seed_tenant: SeedTenant, cleanup_emails: list[str]
) -> None:
    owner = seed_tenant(role="owner")
    invited_email = f"convidado-{secrets.token_hex(6)}@example.com"
    cleanup_emails.append(invited_email)

    invite_token = client.post(
        "/api/v1/users/invite",
        headers=owner.auth_header,
        json={"email": invited_email, "role": "gestor"},
    ).json()["invite_token"]

    body = {"token": invite_token, "nome": "Convidado", "password": "senha12345"}
    assert client.post("/api/v1/auth/accept-invite", json=body).status_code == 204
    # Segundo uso do mesmo convite → 401 (accepted_at já preenchido).
    assert client.post("/api/v1/auth/accept-invite", json=body).status_code == 401


def test_invite_por_role_sem_permissao_retorna_403(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    gestor = seed_tenant(role="gestor")  # require_roles("owner", "admin")

    resp = client.post(
        "/api/v1/users/invite",
        headers=gestor.auth_header,
        json={"email": "alguem@example.com", "role": "viewer"},
    )
    assert resp.status_code == 403


def test_invite_sem_autenticacao_retorna_401(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/users/invite",
        json={"email": "alguem@example.com", "role": "viewer"},
    )
    assert resp.status_code == 401


def test_invite_role_invalida_retorna_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    # `ai` não é um papel convidável (atribuído só via fluxo de agentes).
    resp = client.post(
        "/api/v1/users/invite",
        headers=owner.auth_header,
        json={"email": "alguem@example.com", "role": "ai"},
    )
    assert resp.status_code == 422


def test_accept_invite_senha_curta_retorna_422(client: TestClient) -> None:
    # Validação de schema (password min 8) roda antes de tocar o banco.
    resp = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": "qualquer", "nome": "X", "password": "1234567"},
    )
    assert resp.status_code == 422
