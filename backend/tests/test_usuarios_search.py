"""US-07 — GET /usuarios: lista/busca usuários do tenant para o seletor de
membros e menções. Isolamento por empresa via RLS de user_company_role.
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
MakeUser = Callable[..., tuple[str, str, str]]


@pytest.fixture
def seed_user() -> Iterator[MakeUser]:
    created: list[str] = []

    def _make(company_id: str, *, nome: str, role: str = "campo") -> tuple[str, str, str]:
        email = f"user-{uuid.uuid4().hex[:8]}@example.com"
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
        return str(uid), nome, email

    yield _make

    with SessionLocal() as session:
        for uid in created:
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        session.commit()


def test_lista_usuarios_do_tenant(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    uid, nome, email = seed_user(owner.company_id, nome="Ana Engenheira")

    resp = client.get("/api/v1/usuarios", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    ids = {u["id"] for u in items}
    # O próprio owner + o usuário semeado aparecem.
    assert owner.user_id in ids
    assert uid in ids
    achado = next(u for u in items if u["id"] == uid)
    assert achado["nome"] == nome
    assert achado["email"] == email
    assert achado["role"] == "campo"


def test_busca_por_nome(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner = seed_tenant(role="owner")
    seed_user(owner.company_id, nome="Carlos Pedreiro")
    seed_user(owner.company_id, nome="Mariana Arquiteta")

    resp = client.get("/api/v1/usuarios", headers=owner.auth_header, params={"search": "arquit"})
    assert resp.status_code == 200
    nomes = [u["nome"] for u in resp.json()["items"]]
    assert "Mariana Arquiteta" in nomes
    assert "Carlos Pedreiro" not in nomes


def test_nao_vaza_usuarios_de_outro_tenant(
    client: TestClient, seed_tenant: SeedTenant, seed_user: MakeUser
) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    uid_b, _, _ = seed_user(owner_b.company_id, nome="Intruso da B")

    resp = client.get("/api/v1/usuarios", headers=owner_a.auth_header)
    assert resp.status_code == 200
    ids = {u["id"] for u in resp.json()["items"]}
    assert uid_b not in ids  # RLS isola por empresa


def test_exige_autenticacao(client: TestClient) -> None:
    assert client.get("/api/v1/usuarios").status_code == 401
