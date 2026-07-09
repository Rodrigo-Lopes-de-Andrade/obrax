"""Router do dashboard admin (B4.4, US-01).

`GET /dashboard/summary` — KPIs agregados do tenant. Leitura aberta a qualquer
usuário autenticado (todos veem o dashboard). Cache com TTL de 60s por tenant
(docs/SPRINTS.md B4.4): tolera defasagem e mantém a resposta barata; o cache é
um ponto de extensão (in-process hoje, Redis em prod — ver
app/integrations/cache.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant
from app.integrations.cache import Cache, get_dashboard_cache
from app.modules.gestao.dashboard import service
from app.modules.gestao.dashboard.schemas import DashboardSummary

router = APIRouter(tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
    cache: Cache = Depends(get_dashboard_cache),
) -> DashboardSummary:
    key = f"dashboard:summary:{company_id}"
    cached = cache.get(key)
    if isinstance(cached, DashboardSummary):
        return cached
    summary = service.compute_summary(session)
    cache.set(key, summary)
    return summary
