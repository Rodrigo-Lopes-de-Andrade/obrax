"""Agrega os routers de módulo sob o prefixo `/api/v1` (montado em `app.main`)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.gestao.checklist.router import router as checklist_router
from app.modules.gestao.clientes.router import router as clientes_router
from app.modules.gestao.dashboard.router import router as dashboard_router
from app.modules.gestao.documentos.router import router as documentos_router
from app.modules.gestao.equipes.router import router as equipes_router
from app.modules.gestao.fotos.router import router as fotos_router
from app.modules.gestao.obras.router import router as obras_router
from app.modules.gestao.ocorrencias.router import router as ocorrencias_router
from app.modules.gestao.relatorios.router import router as relatorios_router
from app.modules.gestao.tickets.router import router as tickets_router
from app.modules.orcamento.routers.insumos import router as insumos_router
from app.modules.orcamento.routers.itens import router as orcamento_itens_router
from app.modules.orcamento.routers.orcamentos import router as orcamentos_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
api_router.include_router(obras_router, prefix="/obras", tags=["obras"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(relatorios_router, prefix="/relatorios", tags=["relatorios"])
# Sem prefixo: paths absolutos (/obras/{id}/documentos e /documentos/{id}/confirm).
api_router.include_router(documentos_router)
# Sem prefixo: paths absolutos aninhados (/obras/{id}/membros).
api_router.include_router(equipes_router)
# Sem prefixo: paths absolutos (/obras/{id}/checklist e /checklist/{id}).
api_router.include_router(checklist_router)
# Sem prefixo: paths absolutos (/obras/{id}/tickets e /tickets*).
api_router.include_router(tickets_router)
# Sem prefixo: paths absolutos (/photos/sync, /photos/{id}/confirm, /obras/{id}/photos).
api_router.include_router(fotos_router)
# Sem prefixo: paths absolutos (/obras/{id}/ocorrencias e /ocorrencias/{id}).
api_router.include_router(ocorrencias_router)
# Sem prefixo: paths absolutos (/obras/{id}/orcamentos e /orcamentos*).
api_router.include_router(orcamentos_router)
# Sem prefixo: paths absolutos (/orcamentos/versoes/{id}/itens* e /orcamentos/itens*).
api_router.include_router(orcamento_itens_router)
# Sem prefixo: paths absolutos (/insumos e /insumos/categorias).
api_router.include_router(insumos_router)
