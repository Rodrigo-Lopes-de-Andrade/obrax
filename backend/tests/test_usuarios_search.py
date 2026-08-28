"""`GET /api/v1/usuarios` — seletor de usuários do tenant (US-07).

Alimenta o combo de "adicionar membro" no frontend. Leitura aberta a qualquer
role autenticado; o isolamento vem da RLS de `user_company_role` (o JOIN é o que
limita `users`, que é uma tabela de identidade global sem `company_id`).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]
MakeUser = Callable[..., str]


@pytest.fixture
def seed_user() -> Iterator[MakeUser]:
    """Cria um usuário + vínculo numa empresa via `obrax` (bypassa RLS)."""
    created: list[str] = []

    def _make(company_id: str, *, nome: str, email: str, role: str = "campo") -> str:
        with SessionLocal() as session:
            uid = session.execute(
                text(
                    "INSERT INTO users (email, password_hash, nome) "
                    "VALUES (:email, 'x', :nome) RETURNING id"
                ),
                {"email": email, "nome": nome},
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
        return str(uid)

    yield _make

    with SessionLocal() as session:
        for uid in created:
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        session.commit()


def test_lista_usuarios_do_tenant(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    sufixo = uuid.uuid4().hex[:8]
    seed_user(owner.company_id, nome="Ana Ribeiro", email=f"ana-{sufixo}@example.com")
    seed_user(owner.company_id, nome="Bruno Costa", email=f"bruno-{sufixo}@example.com")

    resp = client.get("/api/v1/usuarios", headers=owner.auth_header)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["next_cursor"] is None
    nomes = [u["nome"] for u in body["items"]]
    # Ordenado por nome; o próprio owner ("Teste") também é do tenant.
    assert nomes == ["Ana Ribeiro", "Bruno Costa", "Teste"]
    assert body["items"][0]["role"] == "campo"


def test_search_filtra_por_nome_ou_email(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    sufixo = uuid.uuid4().hex[:8]
    seed_user(owner.company_id, nome="Ana Ribeiro", email=f"ana-{sufixo}@example.com")
    seed_user(owner.company_id, nome="Bruno Costa", email=f"bruno-{sufixo}@example.com")

    por_nome = client.get("/api/v1/usuarios?search=ribeiro", headers=owner.auth_header).json()
    assert [u["nome"] for u in por_nome["items"]] == ["Ana Ribeiro"]

    por_email = client.get(f"/api/v1/usuarios?search=bruno-{sufixo}", headers=owner.auth_header)
    assert [u["nome"] for u in por_email.json()["items"]] == ["Bruno Costa"]


def test_nao_vaza_usuario_de_outro_tenant(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    sufixo = uuid.uuid4().hex[:8]
    seed_user(owner_b.company_id, nome="Zelia do Tenant B", email=f"zelia-{sufixo}@example.com")

    body = client.get("/api/v1/usuarios", headers=owner_a.auth_header).json()

    emails = [u["email"] for u in body["items"]]
    assert emails == [owner_a.email]


def test_limit_fora_do_intervalo_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    assert client.get("/api/v1/usuarios?limit=101", headers=owner.auth_header).status_code == 422


def test_sem_token_401(client: TestClient) -> None:
    assert client.get("/api/v1/usuarios").status_code == 401
