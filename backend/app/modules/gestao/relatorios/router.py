"""Router dos relatórios gerenciais (B6.5, US-10).

`GET /relatorios/obras-ativas` e `GET /relatorios/orcamentos` — agregações por
status do tenant. Leitura aberta a qualquer usuário autenticado (a RLS já limita
ao tenant). Cache com TTL de 5min por tenant (docs/SPRINTS.md B6.5): tolera
defasagem e mantém a resposta barata; o cache é um ponto de extensão (in-process
hoje, Redis em prod — ver app/integrations/cache.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_tenant
from app.integrations.cache import Cache, get_relatorios_cache
from app.modules.gestao.relatorios import service
from app.modules.gestao.relatorios.schemas import RelatorioObrasAtivas, RelatorioOrcamentos

router = APIRouter(tags=["relatorios"])


@router.get("/obras-ativas", response_model=RelatorioObrasAtivas)
def relatorio_obras_ativas(
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
    cache: Cache = Depends(get_relatorios_cache),
) -> RelatorioObrasAtivas:
    key = f"relatorios:obras-ativas:{company_id}"
    cached = cache.get(key)
    if isinstance(cached, RelatorioObrasAtivas):
        return cached
    report = service.obras_ativas(session)
    cache.set(key, report)
    return report


@router.get("/orcamentos", response_model=RelatorioOrcamentos)
def relatorio_orcamentos(
    company_id: str = Depends(get_tenant),
    session: Session = Depends(get_db),
    cache: Cache = Depends(get_relatorios_cache),
) -> RelatorioOrcamentos:
    key = f"relatorios:orcamentos:{company_id}"
    cached = cache.get(key)
    if isinstance(cached, RelatorioOrcamentos):
        return cached
    report = service.orcamentos(session)
    cache.set(key, report)
    return report
