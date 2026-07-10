"""App factory FastAPI — ver docs/CLAUDE.md > Mapa de Arquitetura."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.integrations.storage import storage_healthy

# RFC 7807 Problem Details — formato de erro obrigatório (docs/CLAUDE.md >
# Contrato Front <-> Back > Convenções).


def _problem_response(
    *,
    status_code: int,
    title: str,
    detail: Any,
    instance: str,
    errors: list[Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if errors is not None:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content)


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    response = _problem_response(
        status_code=exc.status_code,
        title=str(exc.detail),
        detail=exc.detail,
        instance=request.url.path,
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="validation_error",
        detail="Erro de validação da requisição",
        instance=request.url.path,
        # jsonable_encoder: `exc.errors()` pode conter o objeto `ValueError`
        # cru em `ctx` (validators que levantam ValueError) — não serializável.
        errors=jsonable_encoder(exc.errors()),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Obrax API", version="0.1.0")

    app.add_middleware(TenantMiddleware)

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        # B8.5: reporta conectividade do storage e status do realtime. É um
        # relatório (sempre 200), não um gate — `storage_healthy` é best-effort.
        # Realtime é "ok" quando ligado e configurado; senão "disabled" (dev/CI).
        realtime_ok = (
            settings.realtime_enabled
            and bool(settings.supabase_url)
            and bool(settings.supabase_service_key)
        )
        return {
            "status": "ok",
            "storage": "ok" if storage_healthy() else "error",
            "realtime": "ok" if realtime_ok else "disabled",
        }

    return app


app = create_app()
