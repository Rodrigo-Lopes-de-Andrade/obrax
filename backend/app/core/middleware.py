"""TenantMiddleware — decodifica o JWT de acesso de cada request e injeta o
contexto de tenant em `request.state.auth` (docs/ESPEC.md § 3).

Importante: `SET LOCAL app.company_id` só pode ser executado dentro da mesma
transação/conexão que vai rodar as queries da request — e essa conexão só é
aberta pela dependency `app.core.deps.get_db`, não pelo middleware (ASGI
middleware não tem acesso ao sistema de dependências do FastAPI). Por isso a
responsabilidade é dividida:

1. TenantMiddleware (aqui): decodifica o token e popula `request.state.auth`.
2. `get_tenant`/`get_db` (app/core/deps.py): leem `request.state.auth` e
   aplicam de fato o `SET LOCAL app.company_id` na sessão da request.

Requests sem `Authorization: Bearer <token>` válido simplesmente não ganham
contexto (`request.state.auth = None`) — endpoints públicos (`/health`,
`/api/v1/auth/login`, etc.) não dependem dele; endpoints protegidos usam
`Depends(get_current_user)`/`Depends(get_tenant)`, que levantam 401 nesse
caso ("Sem company_id no contexto → erro").
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_token


@dataclass(frozen=True)
class AuthContext:
    user_id: uuid.UUID
    company_id: uuid.UUID
    role: str
    perms: list[str]
    jti: str


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.auth = None
        authorization = request.headers.get("authorization")
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[len("bearer ") :]
            try:
                payload = decode_token(token, expected_type="access")
            except jwt.PyJWTError:
                pass  # token ausente/expirado/inválido → sem contexto de tenant
            else:
                request.state.auth = AuthContext(
                    user_id=uuid.UUID(payload["sub"]),
                    company_id=uuid.UUID(payload["company_id"]),
                    role=payload["role"],
                    perms=list(payload.get("perms", [])),
                    jti=payload["jti"],
                )
        return await call_next(request)
