"""B8.2/B8.3 — sync de fotos de campo (presigned PUT + confirm, dedup, realtime).

Teste de integração real contra o MinIO local (docker-compose): o sync devolve
uma URL assinada, o teste sobe os bytes com um `PUT` de verdade e o confirm
valida tamanho + SHA-256 baixando o objeto. Requer a stack local (`make up`).
O publisher de realtime é substituído por um fake gravador via
`dependency_overrides` (dev/CI não têm Supabase). Objetos são removidos no
teardown (`cleanup_objects`).
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
from app.core.security import create_access_token
from app.integrations.events import DomainEvent, get_event_publisher
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"
CAPTURED_AT = "2026-07-10T12:00:00Z"


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


@pytest.fixture
def recorder() -> Iterator[RecordingPublisher]:
    rec = RecordingPublisher()
    app.dependency_overrides[get_event_publisher] = lambda: rec
    yield rec
    app.dependency_overrides.pop(get_event_publisher, None)


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
    keys: list[str] = []
    yield keys.append
    client = _storage_admin()
    for key in keys:
        client.delete_object(Bucket=settings.storage_bucket_documents, Key=key)


def _seed_obra(client: TestClient, owner: SeededUser) -> str:
    cliente_id = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente da Obra"},
    ).json()["id"]
    resp = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cliente_id, "codigo": "OBR-001", "nome": "Reforma X"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _sync_body(content: bytes, obra_id: str, **over: object) -> dict:
    base: dict = {
        "obra_id": obra_id,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
        "captured_at": CAPTURED_AT,
    }
    base.update(over)
    return base


def _headers(owner: SeededUser, client_photo_id: str) -> dict[str, str]:
    return {**owner.auth_header, "Idempotency-Key": client_photo_id}


def _put(url: str, content: bytes) -> None:
    req = urllib.request.Request(url, data=content, method="PUT")
    with urllib.request.urlopen(req) as r:  # noqa: S310
        assert r.status == 200


def test_sync_confirm_fluxo_completo(
    client: TestClient,
    seed_tenant: SeedTenant,
    cleanup_objects: Callable[[str], None],
    recorder: RecordingPublisher,
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"conteudo binario da foto de teste"
    cpid = str(uuid.uuid4())

    resp = client.post(
        "/api/v1/photos/sync", headers=_headers(owner, cpid), json=_sync_body(content, obra_id)
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    photo_id = body["photo_id"]
    assert uuid.UUID(photo_id)
    assert body["method"] == "PUT"
    assert body["expires_in"] == settings.storage_presign_ttl
    cleanup_objects(f"{owner.company_id}/{obra_id}/{photo_id}")

    _put(body["upload_url"], content)

    resp = client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    foto = resp.json()
    assert foto["sync_status"] == "sincronizado"
    assert foto["synced_at"] is not None
    assert foto["client_photo_id"] == cpid
    assert foto["download_url"] is not None
    assert foto["size_bytes"] == len(content)

    # Evento de realtime na galeria da obra.
    assert len(recorder.events) == 1
    ev = recorder.events[0]
    assert ev.channel == f"obra:{obra_id}:fotos"
    assert ev.event == "foto.sincronizada"
    assert ev.payload["id"] == photo_id

    # Galeria lista a foto confirmada.
    page = client.get(f"/api/v1/obras/{obra_id}/photos", headers=owner.auth_header).json()
    assert [p["id"] for p in page["items"]] == [photo_id]


def test_campo_pode_sincronizar(client: TestClient, seed_tenant: SeedTenant) -> None:
    """Capturar foto é ação de campo: o role `campo` está nas write roles. A obra
    é criada pelo owner; forjamos um token `campo` para a MESMA empresa (a RLS
    enxerga a obra) e sincronizamos com sucesso."""
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    campo_token = create_access_token(
        user_id=uuid.UUID(owner.user_id),
        company_id=uuid.UUID(owner.company_id),
        role="campo",
    ).token
    resp = client.post(
        "/api/v1/photos/sync",
        headers={"Authorization": f"Bearer {campo_token}", "Idempotency-Key": str(uuid.uuid4())},
        json=_sync_body(b"foto do campo", obra_id),
    )
    assert resp.status_code == 201, resp.text


def test_idempotente_mesmo_client_id(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"foto idempotente"
    cpid = str(uuid.uuid4())

    r1 = client.post(
        "/api/v1/photos/sync", headers=_headers(owner, cpid), json=_sync_body(content, obra_id)
    )
    r2 = client.post(
        "/api/v1/photos/sync", headers=_headers(owner, cpid), json=_sync_body(content, obra_id)
    )
    assert r1.status_code == 201 and r2.status_code == 201
    # Mesma chave do aparelho → mesma linha (retry após queda de rede).
    assert r1.json()["photo_id"] == r2.json()["photo_id"]


def test_ja_sincronizada_409(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"foto ja sincronizada"
    cpid = str(uuid.uuid4())
    body = client.post(
        "/api/v1/photos/sync", headers=_headers(owner, cpid), json=_sync_body(content, obra_id)
    ).json()
    photo_id = body["photo_id"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{photo_id}")
    _put(body["upload_url"], content)
    client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)

    # Re-sync da mesma foto já sincronizada → 409 (o cliente tira da fila).
    resp = client.post(
        "/api/v1/photos/sync", headers=_headers(owner, cpid), json=_sync_body(content, obra_id)
    )
    assert resp.status_code == 409


def test_dedup_conteudo_409(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"mesmo conteudo, aparelhos diferentes"
    # Duas chaves de aparelho distintas, mesmo sha256 → segunda é dup de conteúdo.
    client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(content, obra_id),
    )
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(content, obra_id),
    )
    assert resp.status_code == 409


def test_confirm_sem_upload_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    body = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(b"nunca enviado", obra_id),
    ).json()
    resp = client.post(f"/api/v1/photos/{body['photo_id']}/confirm", headers=owner.auth_header)
    assert resp.status_code == 422


def test_confirm_hash_divergente_422(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    declarado = b"conteudo declarado"
    # Declara o sha/size do `declarado`, mas sobe outro conteúdo do MESMO tamanho
    # (mesma len → passa a checagem de tamanho, cai na de hash).
    outro = b"X" * len(declarado)
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(declarado, obra_id),
    )
    body = resp.json()
    photo_id = body["photo_id"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{photo_id}")
    _put(body["upload_url"], outro)  # mesmo tamanho, sha diferente
    resp = client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 422


def test_confirm_tamanho_divergente_422(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"dez bytes!"
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        # Declara 999 bytes mas sobe menos → HEAD detecta divergência.
        json=_sync_body(content, obra_id, size_bytes=999),
    )
    body = resp.json()
    photo_id = body["photo_id"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{photo_id}")
    _put(body["upload_url"], content)
    resp = client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)
    assert resp.status_code == 422


def test_confirm_idempotente(
    client: TestClient, seed_tenant: SeedTenant, cleanup_objects: Callable[[str], None]
) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    content = b"confirma duas vezes"
    body = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(content, obra_id),
    ).json()
    photo_id = body["photo_id"]
    cleanup_objects(f"{owner.company_id}/{obra_id}/{photo_id}")
    _put(body["upload_url"], content)
    r1 = client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)
    r2 = client.post(f"/api/v1/photos/{photo_id}/confirm", headers=owner.auth_header)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["sync_status"] == "sincronizado"


def test_sync_sem_idempotency_key_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    # Sem header Idempotency-Key → 422 (header obrigatório, docs/CLAUDE.md).
    resp = client.post(
        "/api/v1/photos/sync", headers=owner.auth_header, json=_sync_body(b"x", obra_id)
    )
    assert resp.status_code == 422


def test_sync_size_acima_2mb_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    obra_id = _seed_obra(client, owner)
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(b"x", obra_id, size_bytes=2 * 1024 * 1024 + 1, sha256="a" * 64),
    )
    assert resp.status_code == 422


def test_sync_viewer_403(client: TestClient, seed_tenant: SeedTenant) -> None:
    viewer = seed_tenant(role="viewer")
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(viewer, str(uuid.uuid4())),
        json=_sync_body(b"x", str(uuid.uuid4()), sha256="a" * 64),
    )
    assert resp.status_code == 403


def test_sync_obra_inexistente_422(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/photos/sync",
        headers=_headers(owner, str(uuid.uuid4())),
        json=_sync_body(b"x", str(uuid.uuid4()), sha256="a" * 64),
    )
    assert resp.status_code == 422


def test_gallery_cross_tenant_404(client: TestClient, seed_tenant: SeedTenant) -> None:
    owner_a = seed_tenant(role="owner")
    owner_b = seed_tenant(role="owner")
    obra_b = _seed_obra(client, owner_b)
    # Tenant A não enxerga a obra de B (RLS) → 404 na galeria.
    resp = client.get(f"/api/v1/obras/{obra_b}/photos", headers=owner_a.auth_header)
    assert resp.status_code == 404
