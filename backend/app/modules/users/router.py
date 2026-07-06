"""Router `/api/v1/users` — convite de usuário (admin/owner apenas)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant, require_roles
from app.modules.users import service
from app.modules.users.schemas import InviteListItem, InviteRequest, InviteResponse

router = APIRouter()


@router.post(
    "/invite",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("owner", "admin"))],
)
def invite_user(
    payload: InviteRequest,
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
) -> InviteResponse:
    raw_token, expires_at = service.create_invite(
        session, company_id=company_id, email=payload.email, role=payload.role
    )
    return InviteResponse(
        email=payload.email, role=payload.role, expires_at=expires_at, invite_token=raw_token
    )


@router.get(
    "/invite",
    response_model=list[InviteListItem],
    dependencies=[Depends(require_roles("owner", "admin"))],
)
def list_invites(session: Session = Depends(get_db)) -> list[InviteListItem]:
    """Lista convites pendentes/aceitos do tenant autenticado. RLS (via
    `get_db`) garante que só os convites da própria empresa aparecem — ver
    `tests/test_tenant_isolation_api.py`."""
    return [InviteListItem.model_validate(row) for row in service.list_invites(session)]
