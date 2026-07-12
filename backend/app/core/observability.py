"""Observabilidade de request (B11.1) + tracing distribuído (B11.2, seam).

`RequestContextMiddleware`: gera/propaga um `X-Request-Id`, popula os contextvars
de logging (request_id + company_id) e emite uma linha de log de acesso por
request, com método, rota, status e duração. Substitui o access-log do uvicorn
(desligado em `configure_logging`) para que o acesso saia no mesmo formato
estruturado do resto.

`configure_tracing`: seam de OpenTelemetry. No-op a menos que
`OTEL_EXPORTER_OTLP_ENDPOINT` esteja definido E os pacotes `opentelemetry-*`
estejam instalados — assim o app roda sem OTel em dev/CI e a ativação em
staging/prod é só instalar os pacotes + setar a env (ver docs/DEVOPS).
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import company_id_var, get_logger, request_id_var

logger = get_logger("obrax.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        rid_token = request_id_var.set(request_id)
        # company_id vem do TenantMiddleware, que roda antes? A ordem de
        # middlewares no Starlette é LIFO: quem é adicionado por último roda por
        # fora. Lemos request.state.auth se já estiver populado; senão fica "-".
        auth = getattr(request.state, "auth", None)
        cid_token = company_id_var.set(str(auth.company_id) if auth else "-")

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.info(
                "%s %s -> %s (%sms)",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": status_code,
                    "duration_ms": elapsed_ms,
                },
            )
            company_id_var.reset(cid_token)
            request_id_var.reset(rid_token)


def configure_tracing(app: object) -> bool:
    """Instrumenta o app com OpenTelemetry se configurado. Retorna True se ligou.

    Guardado por env + import opcional: sem `OTEL_EXPORTER_OTLP_ENDPOINT` ou sem
    os pacotes instalados, é no-op silencioso (dev/CI).
    """
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False
    try:
        from opentelemetry.instrumentation.fastapi import (  # type: ignore[import-not-found]
            FastAPIInstrumentor,
        )
    except ImportError:
        get_logger("obrax.otel").warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT definido mas pacotes opentelemetry-* "
            "não instalados; tracing desligado.",
        )
        return False
    FastAPIInstrumentor.instrument_app(app)
    get_logger("obrax.otel").info("OpenTelemetry instrumentado no app FastAPI.")
    return True
