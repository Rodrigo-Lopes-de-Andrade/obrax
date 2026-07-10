"""Cliente de object store S3-compatível (B3.2 / GED).

Supabase Storage é S3-compatível, então o mesmo `S3StorageClient` (boto3) serve
tanto o MinIO local (dev, ver docker-compose.yml) quanto o endpoint S3 do
Supabase em staging/prod — a diferença é só o `endpoint_url`/credenciais em
`app.core.config`. Endereçamento path-style + assinatura s3v4 (exigidos por
MinIO/Supabase; virtual-host style quebra com `localhost`/`endpoint` custom).

O upload nunca passa pela API: o backend só assina uma URL de `PUT` (TTL curto)
e o cliente sobe o arquivo direto no bucket (docs/ESPEC.md § 7). Regra do
projeto: nunca persistir a URL assinada — guardamos apenas o `storage_path`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    method: str
    expires_in: int


@dataclass(frozen=True)
class ObjectStat:
    size_bytes: int


class StorageClient(Protocol):
    """Contrato mínimo usado pelos módulos de documentos e PDF. Tests injetam um
    fake (ver conftest) para não depender de rede."""

    def presigned_put_url(self, *, key: str) -> PresignedUpload: ...

    def stat(self, *, key: str) -> ObjectStat | None:
        """Metadados do objeto (HEAD) ou `None` se ele não existe."""
        ...

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        """Sobe bytes gerados no servidor (ex.: PDF do orçamento). Diferente do
        upload de documentos (presigned PUT direto do cliente), aqui o artefato
        nasce no backend, então subimos server-side."""
        ...

    def get_object(self, *, key: str) -> bytes:
        """Baixa os bytes do objeto. Usado no confirm da foto para validar o
        SHA-256 server-side (o cliente sobe direto no bucket, sem passar pela
        API — então o hash informado precisa ser conferido contra o conteúdo)."""
        ...

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        """URL de download assinada (GET) com TTL. Nunca é persistida — é gerada
        sob demanda a cada leitura."""
        ...


class S3StorageClient:
    def __init__(self, *, bucket: str) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def presigned_put_url(self, *, key: str) -> PresignedUpload:
        ttl = settings.storage_presign_ttl
        url = self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=ttl,
            HttpMethod="PUT",
        )
        return PresignedUpload(url=url, method="PUT", expires_in=ttl)

    def stat(self, *, key: str) -> ObjectStat | None:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return None
            raise
        return ObjectStat(size_bytes=int(head["ContentLength"]))

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=body, ContentType=content_type)

    def get_object(self, *, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()  # type: ignore[no-any-return]

    def presigned_get_url(self, *, key: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(  # type: ignore[no-any-return]
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )

    def ensure_bucket(self) -> None:
        """Cria o bucket se ainda não existe (idempotente). Em dev os buckets
        vêm do `minio-init`; este helper cobre setup de testes."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                self._client.create_bucket(Bucket=self._bucket)
                return
            raise


@lru_cache
def _documents_client() -> S3StorageClient:
    return S3StorageClient(bucket=settings.storage_bucket_documents)


def get_storage_client() -> StorageClient:
    """Dependency FastAPI: cliente do bucket de documentos (singleton).
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _documents_client()


def storage_healthy() -> bool:
    """Conectividade com o object store (HEAD no bucket) — usado no /health
    (B8.5). Best-effort: qualquer falha (rede, credencial, bucket ausente) vira
    `False`, sem derrubar o endpoint."""
    try:
        client = _documents_client()
        client._client.head_bucket(Bucket=client._bucket)
    except Exception:  # noqa: BLE001 — health é um relatório, não um gate
        return False
    return True
