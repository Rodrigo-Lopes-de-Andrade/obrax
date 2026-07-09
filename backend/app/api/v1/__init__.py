"""Agrega os routers de módulo sob o prefixo `/api/v1` (montado em `app.main`)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.gestao.clientes.router import router as clientes_router
from app.modules.gestao.dashboard.router import router as dashboard_router
from app.modules.gestao.documentos.router import router as documentos_router
from app.modules.gestao.equipes.router import router as equipes_router
from app.modules.gestao.obras.router import router as obras_router
from app.modules.gestao.tickets.router import router as tickets_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
api_router.include_router(obras_router, prefix="/obras", tags=["obras"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
# Sem prefixo: paths absolutos (/obras/{id}/documentos e /documentos/{id}/confirm).
api_router.include_router(documentos_router)
# Sem prefixo: paths absolutos aninhados (/obras/{id}/membros).
api_router.include_router(equipes_router)
# Sem prefixo: paths absolutos (/obras/{id}/tickets e /tickets*).
api_router.include_router(tickets_router)
