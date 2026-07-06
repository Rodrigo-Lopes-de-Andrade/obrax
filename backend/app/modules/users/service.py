"""Criação de convites de usuário (B1.5 / US-19 prep)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.auth.service import generate_invite_token, hash_invite_token

INVITE_TTL = timedelta(days=7)


def create_invite(
    session: Session, *, company_id: str, email: str, role: str
) -> tuple[str, datetime]:
    raw_token = generate_invite_token()
    token_hash = hash_invite_token(raw_token)
    expires_at = datetime.now(UTC) + INVITE_TTL
    session.execute(
        text(
            "INSERT INTO invitations (token_hash, email, company_id, role, expires_at) "
            "VALUES (:token_hash, :email, :company_id, :role, :expires_at)"
        ),
        {
            "token_hash": token_hash,
            "email": email,
            "company_id": company_id,
            "role": role,
            "expires_at": expires_at,
        },
    )
    return raw_token, expires_at


def list_invites(session: Session) -> list[dict[str, object]]:
    """Convites do tenant atual (RLS filtra por `app.company_id` já setado
    pela dependency `get_db`). Usado também como prova de isolamento
    multi-tenant via API — ver `tests/test_tenant_isolation_api.py`."""
    rows = session.execute(
        text(
            "SELECT email, role, expires_at, accepted_at FROM invitations ORDER BY created_at DESC"
        )
    ).all()
    return [{"email": r[0], "role": r[1], "expires_at": r[2], "accepted_at": r[3]} for r in rows]
