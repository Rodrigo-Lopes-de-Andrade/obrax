"""Hashing de senha (Argon2id) e emissão/validação de JWTs (HS256).

Três "tipos" de token, todos assinados com o mesmo `JWT_SECRET` mas
distinguidos pela claim `type`, conforme docs/ESPEC.md § 4:

- `access`  — 15 min, enviado no header `Authorization: Bearer`.
- `refresh` — 30 dias, entregue via cookie httpOnly (nunca no corpo/JS).
- `magic`   — 30 min, single-use (consumo registrado em `consumed_tokens`).

Claims comuns: `sub` (user_id), `company_id`, `type`, `jti`, `iat`, `exp`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
MAGIC_LINK_TTL = timedelta(minutes=30)

_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh", "magic"]


def hash_password(password: str) -> str:
    # passlib não é tipado (ver override em pyproject.toml); ligamos o retorno
    # a uma variável tipada para não vazar `Any` (mypy strict: no-any-return).
    hashed: str = _pwd_context.hash(password)
    return hashed


def verify_password(password: str, password_hash: str) -> bool:
    valid: bool = _pwd_context.verify(password, password_hash)
    return valid


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def create_access_token(
    *, user_id: uuid.UUID, company_id: uuid.UUID, role: str, perms: list[str] | None = None
) -> IssuedToken:
    now = _now()
    exp = now + ACCESS_TOKEN_TTL
    jti = str(uuid.uuid4())
    token = _encode(
        {
            "sub": str(user_id),
            "company_id": str(company_id),
            "role": role,
            "perms": perms or [],
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": jti,
        }
    )
    return IssuedToken(token=token, jti=jti, expires_at=exp)


def create_refresh_token(*, user_id: uuid.UUID, company_id: uuid.UUID) -> IssuedToken:
    now = _now()
    exp = now + REFRESH_TOKEN_TTL
    jti = str(uuid.uuid4())
    token = _encode(
        {
            "sub": str(user_id),
            "company_id": str(company_id),
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": jti,
        }
    )
    return IssuedToken(token=token, jti=jti, expires_at=exp)


def create_magic_link_token(
    *, user_id: uuid.UUID, company_id: uuid.UUID, purpose: str
) -> IssuedToken:
    now = _now()
    exp = now + MAGIC_LINK_TTL
    jti = str(uuid.uuid4())
    token = _encode(
        {
            "sub": str(user_id),
            "company_id": str(company_id),
            "purpose": purpose,
            "type": "magic",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": jti,
        }
    )
    return IssuedToken(token=token, jti=jti, expires_at=exp)


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Decodifica e valida assinatura/expiração. Levanta `jwt.PyJWTError` em
    qualquer falha (assinatura inválida, expirado, claim `type` incorreta).
    """
    payload: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"esperado type={expected_type!r}, recebido {payload.get('type')!r}"
        )
    return payload
