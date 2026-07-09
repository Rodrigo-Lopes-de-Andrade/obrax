"""B3.2 — upload de documentos em duas etapas (presigned PUT + confirm).

Teste de integração real contra o MinIO local (docker-compose): o create
devolve uma URL assinada, o teste sobe os bytes com um `PUT` de verdade e o
confirm valida via HEAD no storage. Requer a stack local de pé (`make up`).
Objetos criados são removidos no teardown (`cleanup_objects`).
"""

from __future__ import annotations

import hashlib
import urllib.request
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import boto3
import pytest
from botocore.config import Config
from starlette.testclient import TestClient

from app.core.config import settings
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"
DUMMY_SHA = "a" * 64


def _storage_admin() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@pytest.fixture
def cleanup_objects() -> Iterator[Callable[[str], None]]:
    """Registra chaves p/ apagar do bucket ao final (evita órfãos no MinIO)."""
    keys: list[str] = []
    yield keys.append
    client = _storage_admin()
    for key in keys:
        client.delete_object(Bucket=settings.storage_bucket_documents, Key=key)


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    resp = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente da Obra"},
    )
    assert resp.status_code == 201
    cliente_id = resp.json()["id"]
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente_id, "codigo": "OBR-001", "nome": "Reforma X"},
    )
    assert resp.status_code == 201
    return str(resp.json()["id"])


def _meta(content: bytes, **over: object) -> dict:
    base: dict = {
        "nome": "planta.pdf",
        "tipo": "projeto",
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }
    base.update(over)
    return base


def test_upload_fluxo_completo(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"conteudo do documento de teste"

    resp = client.post(
        f"/api/v1/obras/{obra_id}/documentos",
        headers=owner.auth_header,
        json=_meta(content, categoria="Projetos"),
    )
    assert resp.status_code == 201
    body = resp.json()
    documento_id = body["documento_id"]
    assert uuid.UUID(documento_id)
    assert body["method"] == "PUT"
    assert body["expires_in"] == settings.storage_presign_ttl
    assert settings.storage_bucket_documents in body["upload_url"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{documento_id}")

    # PUT real na URL assinada (upload direto ao storage, fora da API).
    put = urllib.request.Request(body["upload_url"], data=content, method="PUT")
    with urllib.request.urlopen(put) as r:
        assert r.status == 200

    resp = client.post(f"/api/v1/documentos/{documento_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["confirmed"] is True
    assert doc["size_bytes"] == len(content)
    assert doc["sha256"] == hashlib.sha256(content).hexdigest()
    assert doc["categoria"] == "Projetos"
    assert doc["visivel_cliente"] is False


def test_confirm_sem_upload_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/documentos",
        headers=owner.auth_header,
        json=_meta(b"nunca sera enviado"),
    )
    documento_id = resp.json()["documento_id"]
    # Sem PUT: o objeto não existe no storage → confirm falha.
    resp = client.post(f"/api/v1/documentos/{documento_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 422


def test_confirm_tamanho_divergente_422(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        f"/api/v1/obras/{obra_id}/documentos",
        headers=owner.auth_header,
        # Declara 999 bytes mas sobe menos → HEAD detecta divergência.
        json=_meta(b"x", size_bytes=999, sha256=DUMMY_SHA),
    )
    documento_id = resp.json()["documento_id"]
    upload_url = resp.json()["upload_url"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{documento_id}")

    put = urllib.request.Request(upload_url, data=b"apenas 9", method="PUT")
    with urllib.request.urlopen(put) as r:
        assert r.status == 200

    resp = client.post(f"/api/v1/documentos/{documento_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 422


def test_dedup_mesmo_sha_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    meta = _meta(b"conteudo unico", sha256=DUMMY_SHA)
    resp = client.post(f"/api/v1/obras/{obra_id}/documentos", headers=owner.auth_header, json=meta)
    assert resp.status_code == 201
    # Mesmo (obra, sha256) → duplicado.
    resp = client.post(f"/api/v1/obras/{obra_id}/documentos", headers=owner.auth_header, json=meta)
    assert resp.status_code == 409


def test_create_viewer_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    viewer = seed_tenant(role="viewer")
    # `viewer` não tem obra própria; basta um obra_id qualquer — o 403 (role) é
    # checado antes de qualquer acesso ao recurso.
    resp = client.post(
        f"/api/v1/obras/{uuid.uuid4()}/documentos",
        headers=viewer.auth_header,
        json=_meta(b"x", sha256=DUMMY_SHA),
    )
    assert resp.status_code == 403


def test_create_obra_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        f"/api/v1/obras/{uuid.uuid4()}/documentos",
        headers=owner.auth_header,
        json=_meta(b"x", sha256=DUMMY_SHA),
    )
    assert resp.status_code == 422


def test_create_obra_de_outro_tenant_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    """RLS esconde a obra do tenant B do tenant A → 422 (obra não encontrada)."""
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    resp = client.post(
        f"/api/v1/obras/{obra_b}/documentos",
        headers=owner_a.auth_header,
        json=_meta(b"x", sha256=DUMMY_SHA),
    )
    assert resp.status_code == 422
