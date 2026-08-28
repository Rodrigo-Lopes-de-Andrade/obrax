"""Regras de negócio de autenticação (docs/ESPEC.md § 4):

- `login`/`refresh_access_token`/`logout`: Argon2id + JWT access (15min) +
  refresh (30d, httpOnly cookie). Roda via `app_admin` (BYPASSRLS) — login
  precisa achar o usuário por email *antes* de saber o tenant (RLS de
  `users` exige `app.company_id` já setado, o que ainda não existe aqui).
- `consume_magic_link`: single-use via `consumed_tokens(jti)` — reuso => 401.
- `accept_invite`: cria o usuário + vínculo `user_company_role` na mesma
  transação, via `app_admin` (o convidado só tem o token opaco em mãos,
  sem tenant conhecido) — ver alembic/versions/0005_rls_policies.py sobre a
  policy de INSERT em `users`.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    IssuedToken,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais inválidas"
)


@dataclass(frozen=True)
class AuthTokens:
    access: IssuedToken
    refresh: IssuedToken


def _as_uuid(value: object) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _first_role_any_company(session: Session, *, user_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    """Vínculo empresa/role do usuário, usado no login.

    Premissa Sprint 1: seleção de empresa multi-tenant (usuário com mais de
    um vínculo) fica fora de escopo — usamos o vínculo mais antigo. Uma UI de
    troca de empresa é trabalho futuro (fora de B1.1-B1.5).
    """
    row = session.execute(
        text(
            "SELECT company_id, role FROM user_company_role "
            "WHERE user_id = :uid ORDER BY created_at ASC LIMIT 1"
        ),
        {"uid": str(user_id)},
    ).first()
    if row is None:
        raise _INVALID_CREDENTIALS
    return _as_uuid(row[0]), str(row[1])


def _role_for_company(session: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> str:
    row = session.execute(
        text("SELECT role FROM user_company_role WHERE user_id = :uid AND company_id = :cid"),
        {"uid": str(user_id), "cid": str(company_id)},
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="vínculo empresa/usuário não encontrado",
        )
    return str(row[0])


def login(session: Session, *, email: str, password: str) -> AuthTokens:
    row = session.execute(
        text("SELECT id, password_hash FROM users WHERE email = :email AND deleted_at IS NULL"),
        {"email": email},
    ).first()
    if row is None or not verify_password(password, str(row[1])):
        raise _INVALID_CREDENTIALS

    user_id = _as_uuid(row[0])
    company_id, role = _first_role_any_company(session, user_id=user_id)
    access = create_access_token(user_id=user_id, company_id=company_id, role=role)
    refresh = create_refresh_token(user_id=user_id, company_id=company_id)
    return AuthTokens(access=access, refresh=refresh)


def refresh_access_token(session: Session, *, refresh_token: str) -> IssuedToken:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token inválido ou expirado"
        ) from exc

    jti = str(payload["jti"])
    revoked = session.execute(
        text("SELECT 1 FROM consumed_tokens WHERE jti = :jti"), {"jti": jti}
    ).first()
    if revoked is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token revogado"
        )

    user_id = uuid.UUID(str(payload["sub"]))
    company_id = uuid.UUID(str(payload["company_id"]))
    role = _role_for_company(session, user_id=user_id, company_id=company_id)
    return create_access_token(user_id=user_id, company_id=company_id, role=role)


def logout(session: Session, *, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        return  # já inválido/expirado — nada a revogar

    jti = str(payload["jti"])
    exp = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
    session.execute(
        text(
            "INSERT INTO consumed_tokens (jti, expires_at) VALUES (:jti, :exp) "
            "ON CONFLICT (jti) DO NOTHING"
        ),
        {"jti": jti, "exp": exp},
    )


def consume_magic_link(session: Session, *, token: str) -> AuthTokens:
    try:
        payload = decode_token(token, expected_type="magic")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="magic link inválido ou expirado"
        ) from exc

    jti = str(payload["jti"])
    exp = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
    # INSERT ... ON CONFLICT DO NOTHING RETURNING: check-and-set atômico —
    # evita corrida entre duas consumições concorrentes do mesmo jti.
    inserted = session.execute(
        text(
            "INSERT INTO consumed_tokens (jti, expires_at) VALUES (:jti, :exp) "
            "ON CONFLICT (jti) DO NOTHING RETURNING jti"
        ),
        {"jti": jti, "exp": exp},
    ).first()
    if inserted is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="magic link já utilizado"
        )

    user_id = uuid.UUID(str(payload["sub"]))
    company_id = uuid.UUID(str(payload["company_id"]))
    role = _role_for_company(session, user_id=user_id, company_id=company_id)
    access = create_access_token(user_id=user_id, company_id=company_id, role=role)
    refresh = create_refresh_token(user_id=user_id, company_id=company_id)
    return AuthTokens(access=access, refresh=refresh)


def accept_invite(session: Session, *, token: str, nome: str, password: str) -> None:
    token_hash = hash_invite_token(token)
    row = session.execute(
        text(
            "SELECT company_id, role, expires_at, accepted_at, email "
            "FROM invitations WHERE token_hash = :hash"
        ),
        {"hash": token_hash},
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="convite não encontrado")

    company_id, role, expires_at, accepted_at, email = row
    if accepted_at is not None or expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="convite expirado ou já utilizado"
        )

    password_hash = hash_password(password)
    try:
        user_id = session.execute(
            text(
                "INSERT INTO users (email, password_hash, nome) "
                "VALUES (:email, :password_hash, :nome) RETURNING id"
            ),
            {"email": email, "password_hash": password_hash, "nome": nome},
        ).scalar_one()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="e-mail já possui conta"
        ) from exc

    session.execute(
        text(
            "INSERT INTO user_company_role (company_id, user_id, role) "
            "VALUES (:company_id, :user_id, :role)"
        ),
        {"company_id": str(company_id), "user_id": str(user_id), "role": role},
    )
    session.execute(
        text("UPDATE invitations SET accepted_at = now() WHERE token_hash = :hash"),
        {"hash": token_hash},
    )


def get_me(session: Session, *, user_id: uuid.UUID) -> dict[str, str]:
    """Nome/e-mail do usuário da sessão. Roda sob `get_db` (RLS): a policy
    `users_tenant_select` já restringe ao tenant do JWT."""
    row = session.execute(
        text("SELECT nome, email FROM users WHERE id = :uid AND deleted_at IS NULL"),
        {"uid": str(user_id)},
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="usuário não encontrado"
        )
    return {"nome": str(row[0]), "email": str(row[1])}
