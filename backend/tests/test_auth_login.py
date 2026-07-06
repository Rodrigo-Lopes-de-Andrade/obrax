"""B1.3 — login + JWT/refresh + logout (docs/SPRINTS.md, critério de aceite:
"Login retorna JWT, refresh renova, logout revoga").

Testes de integração ponta a ponta contra a app FastAPI real (TestClient),
usando um usuário semeado com senha Argon2id de verdade.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]


def test_login_ok_retorna_jwt_e_seta_cookie_refresh(
    client: TestClient, seed_tenant: SeedTenant
) -> None:
    user = seed_tenant(password="senha-super-secreta")

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "senha-super-secreta"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900  # ACCESS_TOKEN_TTL = 15 min
    assert body["access_token"]

    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie


def test_login_senha_errada_retorna_401(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant(password="a-senha-certa")

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "senha-errada"},
    )

    assert resp.status_code == 401


def test_login_email_inexistente_retorna_401(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nao-existe@example.com", "password": "qualquer-coisa"},
    )

    assert resp.status_code == 401


def test_refresh_renova_access_token(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant(password="senha12345")
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "senha12345"})

    resp = client.post("/api/v1/auth/refresh")

    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_logout_revoga_refresh_token(client: TestClient, seed_tenant: SeedTenant) -> None:
    user = seed_tenant(password="senha12345")
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "senha12345"})
    # Guarda o valor do refresh antes do logout — depois do logout o cookie é
    # apagado no cliente, então provamos a revogação server-side reenviando o
    # mesmo token manualmente (não apenas a ausência do cookie).
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token is not None

    assert client.post("/api/v1/auth/logout").status_code == 204

    resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_token}"},
    )
    assert resp.status_code == 401


def test_refresh_sem_cookie_retorna_401(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
