"""B11.4 — teste de carga dos fluxos de leitura autenticados (Locust).

Modela uma sessão de usuário admin: faz login uma vez (`on_start`), guarda o JWT
e depois exercita os endpoints de leitura mais quentes (dashboard, lista de
obras, detalhe de obra, clientes, orçamentos, tickets) com pesos que aproximam o
uso real. Só GETs + o POST /auth/login — **não escreve nada** (seguro rodar
contra staging).

SLO alvo (RNF): P95 < 1.5s sob 200 usuários simultâneos.

Uso (ver docs/LOADTEST.md):
    LOADTEST_EMAIL=demo@obrax.com.br LOADTEST_PASSWORD=obraxdemo123 \
      locust -f loadtest/locustfile.py --host http://localhost:8000 \
      --headless -u 200 -r 20 -t 5m
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task

_API = "/api/v1"
_EMAIL = os.environ.get("LOADTEST_EMAIL", "demo@obrax.com.br")
_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "obraxdemo123")


class AdminReadUser(HttpUser):
    """Usuário admin percorrendo as telas de leitura do painel."""

    # Think time entre requests — usuário real não dispara em loop apertado.
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Autentica e guarda o header Authorization da sessão.

        Passamos o header explicitamente em cada request (em vez de mutar
        `self.client.headers`): sob gevent a mutação de headers de sessão
        compartilhada se perde para parte dos requests, causando 401 espúrios.
        """
        self.auth: dict[str, str] = {}
        self.obra_ids: list[str] = []
        # Locust já contabiliza não-2xx como falha do request pelo status code.
        resp = self.client.post(
            f"{_API}/auth/login",
            json={"email": _EMAIL, "password": _PASSWORD},
            name="POST /auth/login",
        )
        if resp.status_code != 200:
            return
        self.auth = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        # Semeia alguns ids de obra para o task de detalhe.
        page = self.client.get(f"{_API}/obras", headers=self.auth, name="GET /obras")
        if page.status_code == 200:
            self.obra_ids = [o["id"] for o in page.json().get("items", [])]

    @task(4)
    def dashboard(self) -> None:
        self.client.get(
            f"{_API}/dashboard/summary", headers=self.auth, name="GET /dashboard/summary"
        )

    @task(4)
    def list_obras(self) -> None:
        self.client.get(f"{_API}/obras", headers=self.auth, name="GET /obras")

    @task(3)
    def obra_detail(self) -> None:
        if not self.obra_ids:
            return
        obra_id = random.choice(self.obra_ids)
        self.client.get(f"{_API}/obras/{obra_id}", headers=self.auth, name="GET /obras/{id}")

    @task(2)
    def list_clientes(self) -> None:
        self.client.get(f"{_API}/clientes", headers=self.auth, name="GET /clientes")

    @task(2)
    def list_orcamentos(self) -> None:
        self.client.get(f"{_API}/orcamentos", headers=self.auth, name="GET /orcamentos")

    @task(1)
    def list_tickets(self) -> None:
        self.client.get(f"{_API}/tickets", headers=self.auth, name="GET /tickets")
