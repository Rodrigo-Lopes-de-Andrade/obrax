"""B3.4 / D3.1 — busca full-text de documentos por nome (+ OCR quando houver).

`GET /obras/{id}/documentos?search=` usa to_tsvector('portuguese') @@
plainto_tsquery — casado pelo índice GIN da 0016. Nomes ASCII de propósito: sem
a extensão unaccent, a config portuguesa é sensível a acento.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable

from starlette.testclient import TestClient

from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente"},
    )
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": resp.json()["id"], "codigo": "OBR-1", "nome": "Reforma"},
    )
    return str(resp.json()["id"])


def _create_doc(
    client: TestClient, owner: SeededUser, obra_id: str, *, nome: str, categoria: str | None = None
) -> str:
    body: dict = {
        "nome": nome,
        "tipo": "outro",
        "sha256": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "size_bytes": 10,
    }
    if categoria is not None:
        body["categoria"] = categoria
    resp = client.post(f"/api/v1/obras/{obra_id}/documentos", headers=owner.auth_header, json=body)
    assert resp.status_code == 201
    return str(resp.json()["documento_id"])


def _search(client: TestClient, owner: SeededUser, obra_id: str, term: str) -> set[str]:
    resp = client.get(
        f"/api/v1/obras/{obra_id}/documentos?search={term}", headers=owner.auth_header
    )
    assert resp.status_code == 200
    return {item["id"] for item in resp.json()["items"]}


def test_busca_por_palavra_do_nome(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    hidraulica = _create_doc(client, owner, obra_id, nome="planta hidraulica.pdf")
    eletrica = _create_doc(client, owner, obra_id, nome="planta eletrica.pdf")
    _create_doc(client, owner, obra_id, nome="contrato social.pdf")

    # "planta" casa as duas plantas; "hidraulica" só uma.
    assert _search(client, owner, obra_id, "planta") == {hidraulica, eletrica}
    assert _search(client, owner, obra_id, "hidraulica") == {hidraulica}


def test_busca_sem_match(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    _create_doc(client, owner, obra_id, nome="planta hidraulica.pdf")
    assert _search(client, owner, obra_id, "inexistente") == set()


def test_busca_vazia_nao_filtra(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    a = _create_doc(client, owner, obra_id, nome="planta.pdf")
    b = _create_doc(client, owner, obra_id, nome="contrato.pdf")
    assert _search(client, owner, obra_id, "   ") == {a, b}


def test_busca_combinada_com_categoria(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    alvo = _create_doc(client, owner, obra_id, nome="planta hidraulica.pdf", categoria="Projetos")
    # Mesmo termo, outra categoria → filtrado fora pela categoria.
    _create_doc(client, owner, obra_id, nome="planta hidraulica revisada.pdf", categoria="Revisoes")

    resp = client.get(
        f"/api/v1/obras/{obra_id}/documentos?search=hidraulica&categoria=Projetos",
        headers=owner.auth_header,
    )
    assert resp.status_code == 200
    assert [item["id"] for item in resp.json()["items"]] == [alvo]
