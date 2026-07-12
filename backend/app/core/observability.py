"""Observabilidade de request (B11.1) + tracing/logs distribuídos (B11.2, seam).

`RequestContextMiddleware`: gera/propaga um `X-Request-Id`, popula os contextvars
de logging (request_id + company_id) e emite uma linha de log de acesso por
request, com método, rota, status e duração. Substitui o access-log do uvicorn
(desligado em `configure_logging`) para que o acesso saia no mesmo formato
estruturado do resto.

`configure_tracing` / `configure_log_export`: seam de OpenTelemetry → OTLP. São
no-op a menos que `OTEL_EXPORTER_OTLP_ENDPOINT` esteja definido E os pacotes
`opentelemetry-*` estejam instalados — assim o app roda sem OTel em dev/CI e a
ativação em staging/prod é só instalar o extra `observability` + setar as envs.

Backend de destino é agnóstico (qualquer coletor OTLP). Para New Relic (US):

    OTEL_SERVICE_NAME=obrax-api
    OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net
    OTEL_EXPORTER_OTLP_HEADERS=api-key=<NEW_RELIC_LICENSE_KEY>
    OTEL_EXPORTER_OTLP_COMPRESSION=gzip

O endpoint/headers são lidos pelos próprios exporters OTLP a partir do ambiente
(spec OTel) — não os parseamos aqui.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

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


def _otlp_enabled() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


def _build_resource() -> Any:
    """Resource OTel com service.name/atributos vindos do ambiente (spec).

    `Resource.create()` já mescla `OTEL_SERVICE_NAME` e `OTEL_RESOURCE_ATTRIBUTES`;
    default de service.name para não subir telemetria anônima. Retorno tipado como
    `Any`: o tipo real (`Resource`) só existe quando o extra está instalado.
    """
    try:
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    except ImportError:
        return None
    default = {} if os.getenv("OTEL_SERVICE_NAME") else {SERVICE_NAME: "obrax-api"}
    return Resource.create(default)


def configure_tracing(app: Any) -> bool:
    """Liga tracing OTLP + instrumenta FastAPI/SQLAlchemy. Retorna True se ligou.

    Guardado por env + import opcional: sem `OTEL_EXPORTER_OTLP_ENDPOINT` ou sem
    os pacotes instalados, é no-op silencioso (dev/CI). `app` é o FastAPI (tipado
    `Any` porque a instrumentação só existe com o extra instalado).
    """
    otel_log = get_logger("obrax.otel")
    if not _otlp_enabled():
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        otel_log.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT definido mas pacotes opentelemetry-* de "
            "tracing não instalados; tracing desligado. (pip install '.[observability]')",
        )
        return False

    provider = TracerProvider(resource=_build_resource())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
    except ImportError:
        pass  # instrumentação de DB é opcional; segue só com spans de HTTP

    otel_log.info(
        "OpenTelemetry tracing ligado (OTLP -> %s).",
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
    )
    return True


def configure_log_export() -> bool:
    """Encaminha os logs da stdlib para o coletor OTLP. Retorna True se ligou.

    Anexa um `LoggingHandler` OTel ao root logger, então cada linha que já sai no
    formato estruturado (ver `core.logging`) também vira um LogRecord OTLP,
    correlacionado ao trace/span ativo. Mesmo gating de env + import opcional.
    """
    otel_log = get_logger("obrax.otel")
    if not _otlp_enabled():
        return False
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    except ImportError:
        otel_log.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT definido mas pacotes opentelemetry-* de "
            "logs não instalados; export de logs desligado.",
        )
        return False

    provider = LoggerProvider(resource=_build_resource())
    provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    logging.getLogger().addHandler(handler)

    otel_log.info("OpenTelemetry log export ligado (OTLP).")
    return True
