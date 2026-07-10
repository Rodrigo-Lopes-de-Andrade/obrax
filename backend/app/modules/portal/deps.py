"""Dependencies do portal do cliente (B9.2, US-19).

O portal é autenticado de forma diferente do resto da API: não há header
`Authorization: Bearer` (a `TenantMiddleware` não popula `request.state.auth`);
a credencial é o **token do portal** que vem no próprio path (`/portal/.../{token}`).

`get_portal_context` decodifica esse token (tipo `portal`) e devolve o escopo
(company + obra). `get_portal_db` abre uma sessão `app_user` (RLS ativa) já com
`SET LOCAL app.company_id` do token — as mesmas garantias de isolamento por
tenant do `get_db`, só que a origem do tenant é o token do portal, não o JWT de
acesso. `app.actor_id` fica vazio (o titular não é um `user`): o trigger de
auditoria o converte em NULL (ver alembic/versions/0011_audit_log.py).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import AppUserSessionLocal
from app.core.deps import _client_ip
from app.core.security import decode_token

_INVALID_LINK = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="link do portal inválido ou expirado"
)


@dataclass(frozen=True)
class PortalContext:
    company_id: uuid.UUID
    obra_id: uuid.UUID
    cliente_id: uuid.UUID | None


def get_portal_context(token: str) -> PortalContext:
    """Decodifica o token do portal (path param `{token}`). 401 em qualquer
    falha (assinatura, expiração, `type` != portal)."""
    try:
        payload = decode_token(token, expected_type="portal")
    except jwt.PyJWTError as exc:
        raise _INVALID_LINK from exc
    cliente_raw = payload.get("cliente_id")
    return PortalContext(
        company_id=uuid.UUID(str(payload["company_id"])),
        obra_id=uuid.UUID(str(payload["obra_id"])),
        cliente_id=uuid.UUID(str(cliente_raw)) if cliente_raw else None,
    )


def get_portal_db(
    request: Request, ctx: PortalContext = Depends(get_portal_context)
) -> Iterator[Session]:
    """Sessão `app_user` (RLS ativa) escopada ao tenant do token do portal.
    `app.actor_id` vazio (sem usuário) → NULL na auditoria; `app.client_ip`
    preenchido para a trilha das ações do portal (ex.: aprovação, B9.3)."""
    session = AppUserSessionLocal()
    try:
        session.execute(
            text(
                "SELECT set_config('app.company_id', :cid, true), "
                "set_config('app.actor_id', '', true), "
                "set_config('app.client_ip', :ip, true)"
            ),
            {"cid": str(ctx.company_id), "ip": _client_ip(request)},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
