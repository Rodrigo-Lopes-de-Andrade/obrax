"""Logging estruturado (B11.1) — sem dependência externa.

Padrão do projeto: infra ligada por env, no-op/enxuta por default. Em dev/CI o
formato é texto legível; em staging/prod defina `LOG_FORMAT=json` para linhas
JSON prontas p/ agregadores (Grafana Loki/Datadog). Cada linha carrega o
`request_id` e o `company_id` do request corrente via `contextvars`, o que dá
rastro fim-a-fim sem passar o contexto manualmente por toda a stack.

Não usamos `structlog` de propósito: a stdlib `logging` + um formatter JSON
cobre o caso sem somar dependência. Se o time quiser structlog depois, o ponto
de troca é só `configure_logging`.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar

# Contexto por request, preenchido pelo RequestContextMiddleware. Default vazio
# para logs fora de um request (startup, jobs).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
company_id_var: ContextVar[str] = ContextVar("company_id", default="-")

_RESERVED = frozenset(
    logging.makeLogRecord({}).__dict__.keys() | {"message", "asctime", "taskName"},
)


class JsonFormatter(logging.Formatter):
    """Formata cada LogRecord como uma linha JSON com o contexto de tenant."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "company_id": company_id_var.get(),
        }
        # Campos extras passados via `logger.info(..., extra={...})`.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    """Formato legível p/ dev, com request_id quando presente."""

    def format(self, record: logging.LogRecord) -> str:
        rid = request_id_var.get()
        prefix = f"[{rid[:8]}] " if rid != "-" else ""
        base = super().format(record)
        return f"{prefix}{base}"


def configure_logging() -> None:
    """Configura o root logger uma vez, idempotente. Chamado no app factory."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    as_json = os.getenv("LOG_FORMAT", "").lower() == "json"

    handler = logging.StreamHandler(sys.stdout)
    if as_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(_TextFormatter("%(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Uvicorn duplica logs de acesso; deixamos o nosso middleware logar o acesso.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
