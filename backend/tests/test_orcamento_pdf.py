"""B6.3 — geração do PDF do orçamento (US-17).

Monta o contexto a partir do banco, renderiza via `PdfRenderer` (dev = HTML) e
sobe no storage guardando **só a chave** (nunca a URL); o GET assina o download
sob demanda. Storage é um fake em memória — o teste do job não depende do MinIO.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from starlette.testclient import TestClient

from app.integrations.storage import ObjectStat, PresignedUpload, get_storage_client
from app.main import app
from tests.conftest import SeededUser

SeedTenant = Callable[..., SeededUser]

CNPJ_VALIDO = "11222333000181"


class FakeStorage:
    """StorageClient em memória: guarda os bytes por chave e assina uma URL de
    download fake — evita depender do MinIO no teste do job."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        return PresignedUpload(url=f"https://fake/put/{key}", method="PUT", expires_in=900)

    def stat(self, *, key: str) -> ObjectStat | None:
        body = self.objects.get(key)
        return ObjectStat(size_bytes=len(body)) if body is not None else None

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = body
        self.content_types[key] = content_type

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake/get/{key}?ttl={expires_in}"


@pytest.fixture
def fake_storage() -> Iterator[FakeStorage]:
    storage = FakeStorage()
    app.dependency_overrides[get_storage_client] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_client, None)


def _bulk(client: TestClient, owner: SeededUser, vid: str, itens: list[dict]) -> dict:
    resp = client.post(
        f"/api/v1/orcamentos/versoes/{vid}/itens/bulk",
        headers=owner.auth_header,
        json={"itens": itens},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _orcamento_vazio(client: TestClient, owner: SeededUser) -> tuple[str, str]:
    """Cria cliente + obra + orçamento (versão 1 vazia). Devolve (orcamento_id, versao_id)."""
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
    return orc["id"], orc["versao"]["id"]


def _orcamento_com_insumos(client: TestClient, owner: SeededUser) -> str:
    """Orçamento com Fase→Serviço→2 insumos (recalcula curva ABC + fases)."""
    orcamento_id, vid = _orcamento_vazio(client, owner)
    fase = _bulk(client, owner, vid, [{"tipo": "F", "descricao": "Fundações", "codigo": "01"}])[
        "itens"
    ][0]
    serv = next(
        i
        for i in _bulk(
            client, owner, vid, [{"tipo": "S", "descricao": "Sapatas", "parent_id": fase["id"]}]
        )["itens"]
        if i["tipo"] == "S"
    )
    _bulk(
        client,
        owner,
        vid,
        [
            {
                "tipo": "I",
                "parent_id": serv["id"],
                "codigo": "SINAPI-01",
                "descricao": "Concreto usinado",
                "unidade": "m³",
                "quantidade": "8",
                "preco_unitario": "100",
            },
            {
                "tipo": "I",
                "parent_id": serv["id"],
                "descricao": "Aço CA-50",
                "unidade": "kg",
                "quantidade": "2",
                "preco_unitario": "10",
            },
        ],
    )
    return orcamento_id


def test_gerar_e_baixar_pdf(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    orcamento_id = _orcamento_com_insumos(client, owner)

    # POST gera e persiste — em dev o artefato é o próprio HTML.
    resp = client.post(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["gerado_em"]
    assert body["content_type"].startswith("text/html")

    # Subiu exatamente 1 objeto, com chave escopada por tenant/orçamento.
    assert len(fake_storage.objects) == 1
    key = next(iter(fake_storage.objects))
    assert key.startswith(f"{owner.company_id}/orcamentos/{orcamento_id}/")
    conteudo = fake_storage.objects[key].decode("utf-8")
    assert conteudo.startswith("<!DOCTYPE html>")
    assert "Tenant Teste Ltda" in conteudo  # razão social da empresa (cabeçalho)
    assert "Concreto usinado" in conteudo  # insumo da EAP
    assert "R$ 820,00" in conteudo  # custo direto (8×100 + 2×10)

    # GET devolve os metadados + URL de download assinada (nunca persistida).
    resp = client.get(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    assert resp.status_code == 200, resp.text
    status_body = resp.json()
    assert status_body["download_url"] == f"https://fake/get/{key}?ttl=3600"
    assert status_body["content_type"].startswith("text/html")
    assert status_body["gerado_em"] == body["gerado_em"]


def test_regerar_sobrescreve_mesma_chave(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    """Regerar o PDF da mesma versão reusa a chave — não acumula objetos."""
    owner = seed_tenant(role="owner")
    orcamento_id = _orcamento_com_insumos(client, owner)

    client.post(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    client.post(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    assert len(fake_storage.objects) == 1


def test_get_pdf_antes_de_gerar_404(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    orcamento_id, _ = _orcamento_vazio(client, owner)

    resp = client.get(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    assert resp.status_code == 404, resp.text


def test_gerar_pdf_orcamento_vazio(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    """Versão sem itens (JSON denormalizado nulo) gera PDF com seções vazias."""
    owner = seed_tenant(role="owner")
    orcamento_id, _ = _orcamento_vazio(client, owner)

    resp = client.post(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=owner.auth_header)
    assert resp.status_code == 201, resp.text
    key = next(iter(fake_storage.objects))
    assert "Sem itens." in fake_storage.objects[key].decode("utf-8")


def test_gerar_pdf_inexistente_404(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    owner = seed_tenant(role="owner")
    resp = client.post(
        "/api/v1/orcamentos/00000000-0000-0000-0000-000000000000/pdf",
        headers=owner.auth_header,
    )
    assert resp.status_code == 404, resp.text


def test_gerar_pdf_requer_role_escrita(
    client: TestClient, seed_tenant: SeedTenant, fake_storage: FakeStorage
) -> None:
    """`viewer` (sem permissão de escrita) não pode gerar PDF → 403."""
    owner = seed_tenant(role="owner")
    viewer = seed_tenant(role="viewer")
    orcamento_id = _orcamento_com_insumos(client, owner)

    resp = client.post(f"/api/v1/orcamentos/{orcamento_id}/pdf", headers=viewer.auth_header)
    assert resp.status_code == 403, resp.text
