"""Dependencies de FastAPI para tenant/auth/sessão de banco.

`get_db` é a dependency que a maioria dos endpoints autenticados deve usar:
abre uma sessão via role `app_user` (sujeito a RLS) e aplica `SET LOCAL
app.company_id` com o tenant do JWT de acesso — nunca deixa uma query rodar
sem tenant setado (docs/ESPEC.md § 3, "Sem company_id explícito no
Repository → raise imediato").

`get_admin_db` é a exceção deliberada: usada apenas nos fluxos que
precisam operar *antes* de existir um tenant conhecido (login por email —
`users` não tem company_id próprio — e aceitar convite — o token é a única
credencial disponível). Conecta como `app_admin` (BYPASSRLS); ver
`docs/ESPEC.md` § "Arquitetura Multi-tenant" e o comentário de
`alembic/versions/0005_rls_policies.py` sobre a policy de INSERT em `users`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import AppAdminSessionLocal, AppUserSessionLocal
from app.core.middleware import AuthContext


def get_current_user(request: Request) -> AuthContext:
    auth: AuthContext | None = getattr(request.state, "auth", None)
    if auth is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="não autenticado")
    return auth


def get_tenant(auth: AuthContext = Depends(get_current_user)) -> str:
    """Retorna o `company_id` (como string) do tenant autenticado na request."""
    return str(auth.company_id)


def require_roles(*roles: str) -> Callable[[AuthContext], AuthContext]:
    def _dependency(auth: AuthContext = Depends(get_current_user)) -> AuthContext:
        if auth.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acesso negado")
        return auth

    return _dependency


def get_db(company_id: str = Depends(get_tenant)) -> Iterator[Session]:
    """Sessão `app_user` (RLS ativa) com `app.company_id` já setado via
    `SET LOCAL` (escopo da transação da request)."""
    session = AppUserSessionLocal()
    try:
        session.execute(
            text("SELECT set_config('app.company_id', :cid, true)"), {"cid": company_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_admin_db() -> Iterator[Session]:
    """Sessão `app_admin` (BYPASSRLS) — só para fluxos pré-tenant (login,
    aceitar convite). Nunca usar em endpoints de domínio comuns."""
    session = AppAdminSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
