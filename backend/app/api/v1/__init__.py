"""Agrega os routers de módulo sob o prefixo `/api/v1` (montado em `app.main`)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.gestao.clientes.router import router as clientes_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
