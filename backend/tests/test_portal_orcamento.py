"""B9.3 — aprovação/rejeição de orçamento pelo portal do cliente (US-20).

Verifica a evidência de conformidade (comentário, assinatura, IP), a mudança de
status, a trava da versão aprovada e o registro em audit_log. Storage é um fake
em memória (a assinatura é "subida" sem tocar o MinIO).
"""

from __future__ import annotations

import base64
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
# data URL de PNG (bytes fake, mas base64 válido) para a assinatura.
ASSINATURA = "data:image/png;base64," + base64.b64encode(b"assinatura-fake-png").decode()


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(url=f"https://fake/put/{key}", method="PUT", expires_in=900)

    def stat(self, *, key: str) -> ObjectStat | None:
        return ObjectStat(size_bytes=1)

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


def _orcamento_aguardando(client: TestClient, owner: SeededUser) -> tuple[str, str, str]:
    """Cria cliente+obra+orçamento e move o status para aguardando_aprovacao.
    Devolve (obra_id, orcamento_id, versao_id)."""
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
    orc = client.post(
        f"/api/v1/obras/{obra['id']}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Orçamento base"},
    ).json()
    resp = client.patch(
        f"/api/v1/orcamentos/{orc['id']}/status",
        headers=owner.auth_header,
        json={"status": "aguardando_aprovacao"},
    )
    assert resp.status_code == 200, resp.text
    return str(obra["id"]), str(orc["id"]), str(orc["versao"]["id"])


def _mint(client: TestClient, owner: SeededUser, obra_id: str) -> str:
    resp = client.post(f"/api/v1/obras/{obra_id}/portal-link", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["token"])


def test_aprovar_orcamento(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, versao_id = _orcamento_aguardando(client, owner)
    token = _mint(client, owner, obra_id)

    # O cliente vê o orçamento aguardando (com preço, sem números internos).
    ver = client.get(f"/api/v1/portal/orcamentos/{token}")
    assert ver.status_code == 200, ver.text
    assert ver.json()["status"] == "aguardando_aprovacao"
    assert "custo_direto" not in ver.json()

    resp = client.post(
        f"/api/v1/portal/orcamentos/{token}/aprovar",
        headers={"X-Forwarded-For": "203.0.113.7"},
        json={"comentario": "De acordo.", "assinado_por": "João Cliente", "assinatura": ASSINATURA},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "aprovado"
    assert body["decisao"] == "aprovado"

    with SessionLocal() as s:
        assert s.execute(
            text("SELECT status FROM orcamento WHERE id = :id"), {"id": orc_id}
        ).scalar_one() == "aprovado"
        assert s.execute(
            text("SELECT is_locked FROM orcamento_versao WHERE id = :id"), {"id": versao_id}
        ).scalar_one() is True
        aprov = s.execute(
            text(
                "SELECT decisao, assinado_por, host(ip) AS ip, assinatura_path "
                "FROM orcamento_aprovacao WHERE orcamento_id = :id"
            ),
            {"id": orc_id},
        ).mappings().one()
        assert aprov["decisao"] == "aprovado"
        assert aprov["assinado_por"] == "João Cliente"
        assert aprov["ip"] == "203.0.113.7"
        assert aprov["assinatura_path"] is not None
        # A mudança de status foi auditada (audit_orcamento, ramo UPDATE).
        audits = s.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE table_name = 'orcamento' AND action = 'UPDATE' AND record_id = :id"
            ),
            {"id": orc_id},
        ).scalar_one()
        assert audits >= 1
    # A assinatura foi guardada no storage.
    assert fake_storage.objects


def test_rejeitar_nao_trava_versao(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, orc_id, versao_id = _orcamento_aguardando(client, owner)
    token = _mint(client, owner, obra_id)

    resp = client.post(
        f"/api/v1/portal/orcamentos/{token}/rejeitar",
        json={"comentario": "Revisar o valor de fundações."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejeitado"

    with SessionLocal() as s:
        assert s.execute(
            text("SELECT status FROM orcamento WHERE id = :id"), {"id": orc_id}
        ).scalar_one() == "rejeitado"
        # Rejeitado pode voltar a revisão — a versão NÃO é travada.
        assert s.execute(
            text("SELECT is_locked FROM orcamento_versao WHERE id = :id"), {"id": versao_id}
        ).scalar_one() is False


def test_reaprovar_conflita_409(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, _orc_id, _versao_id = _orcamento_aguardando(client, owner)
    token = _mint(client, owner, obra_id)

    assert client.post(f"/api/v1/portal/orcamentos/{token}/aprovar", json={}).status_code == 200
    # Já aprovado (não está mais aguardando) → 409.
    again = client.post(f"/api/v1/portal/orcamentos/{token}/aprovar", json={})
    assert again.status_code == 409


def test_assinatura_invalida_422(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    obra_id, _orc_id, _versao_id = _orcamento_aguardando(client, owner)
    token = _mint(client, owner, obra_id)

    resp = client.post(
        f"/api/v1/portal/orcamentos/{token}/aprovar",
        json={"assinatura": "data:image/png;base64,!!!nao-e-base64!!!"},
    )
    assert resp.status_code == 422


def test_sem_orcamento_compartilhavel_404(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    """Orçamento em rascunho não é visível ao cliente."""
    owner = seed_tenant(role="owner")
    cli = client.post(
        "/api/v1/clientes",
        headers=owner.auth_header,
        json={"tipo_pessoa": "PJ", "documento": CNPJ_VALIDO, "nome": "Cliente Beta"},
    ).json()
    obra = client.post(
        "/api/v1/obras",
        headers=owner.auth_header,
        json={"cliente_id": cli["id"], "codigo": "OBR-1", "nome": "Obra"},
    ).json()
    client.post(
        f"/api/v1/obras/{obra['id']}/orcamentos",
        headers=owner.auth_header,
        json={"titulo": "Rascunho"},
    )
    token = _mint(client, owner, str(obra["id"]))
    assert client.get(f"/api/v1/portal/orcamentos/{token}").status_code == 404
