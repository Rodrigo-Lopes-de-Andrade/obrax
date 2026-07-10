"""B9.4 — exportação LGPD: ZIP com os dados do tenant + download com TTL (US-21).

Storage é um fake em memória: o ZIP "sobe" para um dict e o teste o reabre para
conferir os arquivos. Nenhuma dependência do MinIO.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.db import SessionLocal
from app.integrations.storage import ObjectStat, PresignedUpload, get_storage_client
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(url=f"https://fake/put/{key}", method="PUT", expires_in=900)

    def stat(self, *, key: str) -> ObjectStat | None:
        body = self.objects.get(key)
        return ObjectStat(size_bytes=len(body)) if body is not None else None

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = body

    def get_object(self, *, key: str) -> bytes:
        return self.objects.get(key, b"")

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake/get/{key}?ttl={expires_in}"


@pytest.fixture
def fake_storage() -> Iterator[FakeStorage]:
    storage = FakeStorage()
    app.dependency_overrides[get_storage_client] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_client, None)


def _seed_dados(client: TestClient, owner: SeededUser) -> None:
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Construtora Cliente XYZ"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": "OBR-1", "nome": "Residencial Jardim"},
    ).json()
    client.post(
        f"/api/v1/obras/{obra['id']}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orçamento base"},
    )


def test_export_gera_zip_com_todos_arquivos(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    _seed_dados(client, owner)

    resp = client.post(
        "/api/v1/lgpd/requests", headers=owner.auth_header, json={"request_type": "export"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["request_type"] == "export"
    assert body["status"] == "concluido"
    assert body["expires_at"] is not None
    assert body["download_url"].startswith("https://fake/get/")

    # Reabre o ZIP subido e confere o conteúdo.
    assert len(fake_storage.objects) == 1
    zip_bytes = next(iter(fake_storage.objects.values()))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        nomes = set(zf.namelist())
        assert nomes == {
            "clientes.json",
            "obras.json",
            "orcamentos.json",
            "documentos.csv",
            "tickets.json",
        }
        clientes = json.loads(zf.read("clientes.json"))
        assert any(c["nome"] == "Construtora Cliente XYZ" for c in clientes)
        orcamentos = json.loads(zf.read("orcamentos.json"))
        assert any(o["titulo"] == "Orçamento base" for o in orcamentos)
        assert "obra_id" in zf.read("documentos.csv").decode()


def test_download_reassina_link(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    _seed_dados(client, owner)
    req_id = client.post(
        "/api/v1/lgpd/requests", headers=owner.auth_header, json={"request_type": "export"}
    ).json()["id"]

    resp = client.get(f"/api/v1/lgpd/requests/{req_id}/download", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["download_url"].startswith("https://fake/get/")


def test_download_expirado_410(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    with SessionLocal() as s:
        req_id = s.execute(
            text(
                "INSERT INTO lgpd_request "
                "(company_id, request_type, status, payload_path, expires_at) "
                "VALUES (:c, 'export', 'concluido', 'k/old.zip', now() - interval '1 day') "
                "RETURNING id"
            ),
            {"c": owner.company_id},
        ).scalar_one()
        s.commit()

    resp = client.get(f"/api/v1/lgpd/requests/{req_id}/download", headers=owner.auth_header)
    assert resp.status_code == 410


def test_export_exige_owner_admin(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    gestor = seed_tenant(role="gestor")
    resp = client.post(
        "/api/v1/lgpd/requests", headers=gestor.auth_header, json={"request_type": "export"}
    )
    assert resp.status_code == 403


def test_listar_pedidos(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    _seed_dados(client, owner)
    client.post("/api/v1/lgpd/requests", headers=owner.auth_header, json={"request_type": "export"})
    resp = client.get("/api/v1/lgpd/requests", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["request_type"] == "export"
