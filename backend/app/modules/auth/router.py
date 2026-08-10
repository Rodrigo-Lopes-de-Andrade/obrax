"""Router `/api/v1/auth` — login, refresh, logout, magic link, convite.

Nota sobre o refresh cookie: `HttpOnly` + `SameSite=Strict` sempre; `Secure`
liga quando `ENVIRONMENT != "development"` (permite testar via curl/http em
localhost — ver `app/core/config.py`). Escopo (`path`) restrito a
`/api/v1/auth` para minimizar exposição do cookie a outras rotas.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_admin_db, get_current_user
from app.core.middleware import AuthContext
from app.core.security import ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL
from app.modules.auth import service
from app.modules.auth.schemas import (
    AcceptInviteRequest,
    AccessTokenResponse,
    LoginRequest,
    MagicConsumeRequest,
    MeResponse,
)

router = APIRouter()

_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    # Frontend e backend ficam em domínios diferentes em prod (Vercel ↔ Fly), então
    # o cookie de refresh precisa de SameSite=None + Secure para ser enviado no
    # cross-site. Em dev (mesma origem, sem HTTPS) usa Lax (None exige Secure).
    secure = settings.environment != "development"
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        path=_REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_admin_db),
) -> AccessTokenResponse:
    tokens = service.login(session, email=payload.email, password=payload.password)
    _set_refresh_cookie(response, tokens.refresh.token)
    return AccessTokenResponse(
        access_token=tokens.access.token, expires_in=int(ACCESS_TOKEN_TTL.total_seconds())
    )


@router.get("/me", response_model=MeResponse)
def me(
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_admin_db),
) -> MeResponse:
    """Perfil do usuário autenticado (a partir do `sub` do JWT). `nome`/`email`
    vêm da tabela `users`; `role` é o do vínculo carregado no token."""
    row = session.execute(
        text("SELECT nome, email FROM users WHERE id = :id"),
        {"id": auth.user_id},
    ).one()
    return MeResponse(id=str(auth.user_id), nome=row.nome, email=row.email, role=auth.role)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    session: Session = Depends(get_admin_db),
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE_NAME),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token ausente"
        )
    access = service.refresh_access_token(session, refresh_token=refresh_token)
    return AccessTokenResponse(
        access_token=access.token, expires_in=int(ACCESS_TOKEN_TTL.total_seconds())
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    response: Response,
    session: Session = Depends(get_admin_db),
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE_NAME),
) -> None:
    service.logout(session, refresh_token=refresh_token)
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


@router.post("/magic/consume", response_model=AccessTokenResponse)
def consume_magic_link(
    payload: MagicConsumeRequest,
    response: Response,
    session: Session = Depends(get_admin_db),
) -> AccessTokenResponse:
    tokens = service.consume_magic_link(session, token=payload.token)
    _set_refresh_cookie(response, tokens.refresh.token)
    return AccessTokenResponse(
        access_token=tokens.access.token, expires_in=int(ACCESS_TOKEN_TTL.total_seconds())
    )


@router.post("/accept-invite", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def accept_invite(payload: AcceptInviteRequest, session: Session = Depends(get_admin_db)) -> None:
    service.accept_invite(
        session, token=payload.token, nome=payload.nome, password=payload.password
    )
