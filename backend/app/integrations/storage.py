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
    """Contrato mínimo usado pelo módulo de documentos. Tests injetam um fake
    (ver conftest) para não depender de rede."""

    def presigned_put_url(self, *, key: str) -> PresignedUpload: ...

    def stat(self, *, key: str) -> ObjectStat | None:
        """Metadados do objeto (HEAD) ou `None` se ele não existe."""
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
