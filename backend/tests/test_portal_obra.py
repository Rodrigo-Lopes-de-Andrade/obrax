"""B9.2 — portal do cliente: emissão do link (admin) + acesso read-only (US-19).

Storage é um fake em memória (assina URLs falsas) — o teste não depende do MinIO.
Documentos/fotos são semeados direto no banco (role `obrax`, bypassa RLS) com
`storage_path` preenchido, simulando uploads já confirmados.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.core.security import create_portal_token
from app.integrations.storage import ObjectStat, PresignedUpload, get_storage_client
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


class FakeStorage:
    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(url=f"https://fake/put/{key}", method="PUT", expires_in=900)

    def stat(self, *, key: str) -> ObjectStat | None:
        return ObjectStat(size_bytes=1)

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        return None

    def get_object(self, *, key: str) -> bytes:
        return b""

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake/get/{key}?ttl={expires_in}"


@pytest.fixture
def fake_storage() -> Iterator[FakeStorage]:
    storage = FakeStorage()
    app.dependency_overrides[get_storage_client] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_client, None)


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente Beta"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": "OBR-1", "nome": "Residencial Jardim"},
    ).json()
    return str(obra["id"])


def _seed_documento(company_id: str, obra_id: str, *, nome: str, visivel: bool) -> str:
    with SessionLocal() as s:
        doc_id = s.execute(
            text(
                "INSERT INTO documento "
                "(company_id, obra_id, nome, tipo, storage_path, visivel_cliente) "
                "VALUES (:c, :o, :n, 'projeto', :path, :v) RETURNING id"
            ),
            {
                "c": company_id,
                "o": obra_id,
                "n": nome,
                "path": f"{company_id}/{obra_id}/x",
                "v": visivel,
            },
        ).scalar_one()
        s.commit()
    return str(doc_id)


def _mint(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    resp = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["token"])


def test_gerar_link_e_acessar_portal(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    _seed_documento(owner.company_id, obra_id, nome="Planta baixa", visivel=True)

    token = _mint(client, owner, obra_id)
    resp = client.get(f"/api/v1/portal/obras/{token}")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["codigo"] == "OBR-1"
    assert body["nome"] == "Residencial Jardim"
    assert body["construtora"]  # razão social da construtora (branding)
    assert [d["nome"] for d in body["documentos"]] == ["Planta baixa"]
    assert body["documentos"][0]["download_url"].startswith("https://fake/get/")
    # Nada financeiro vaza para o cliente (schema extra=forbid + superfície enxuta).
    assert "valor_contrato" not in body


def test_documento_nao_visivel_omitido(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    _seed_documento(owner.company_id, obra_id, nome="Visível", visivel=True)
    _seed_documento(owner.company_id, obra_id, nome="Interno", visivel=False)

    token = _mint(client, owner, obra_id)
    body = client.get(f"/api/v1/portal/obras/{token}").json()
    nomes = [d["nome"] for d in body["documentos"]]
    assert nomes == ["Visível"]


def test_token_invalido_401(client: TestClient) -> None:
    resp = client.get("/api/v1/portal/obras/nao-e-um-jwt")
    assert resp.status_code == 401


def test_token_tipo_errado_401(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    # Um JWT de acesso válido não serve como token de portal (claim type errada).
    owner = seed_tenant(role="owner")
    resp = client.get(f"/api/v1/portal/obras/{owner.access_token}")
    assert resp.status_code == 401


def test_link_exige_role_de_gestao(client: TestClient, seed_tenant: SeedTenant) -> None:
    campo = seed_tenant(role="campo")
    # 'campo' não pode emitir link — o role gate barra antes de tocar a obra.
    resp = client.post(f"/api/v1/obras/{uuid.uuid4()}/portal-link", headers=campo.auth_header)
    assert resp.status_code == 403


def test_obra_inexistente_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(f"/api/v1/obras/{uuid.uuid4()}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 404


def test_token_forjado_cross_tenant_nao_le_obra(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    """Token com company_id de A mas obra_id de B: a RLS (app.company_id = A)
    esconde a obra de B → 404, mesmo com assinatura JWT válida."""
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)

    forjado = create_portal_token(
        company_id=uuid.uuid4(),  # tenant A (inexistente/diferente)
        obra_id=uuid.UUID(obra_b),
        cliente_id=None,
    ).token
    resp = client.get(f"/api/v1/portal/obras/{forjado}")
    assert resp.status_code == 404
