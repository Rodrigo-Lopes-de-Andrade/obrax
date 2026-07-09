"""Publicação de eventos de domínio para o realtime (B4.3).

Ponto de extensão desacoplado do CRUD: o handler persiste a mensagem e chama
`emit(...)`; *quem entrega* (ou não) o evento é decidido aqui, por ambiente.
Isso mantém o CRUD de tickets sem acoplamento a Supabase (decisão de realtime
em docs/PRD.md): o INSERT não sabe que existe um canal.

- Dev / testes / CI: `NoopEventPublisher` — não entrega nada. O chat do
  frontend em mock simula realtime por update otimista + polling (F4.4/F4.5).
- Staging / prod: `SupabaseEventPublisher` faz *broadcast* no canal Supabase
  Realtime (`realtime/v1/api/broadcast`). Só é selecionado quando
  `REALTIME_ENABLED=true` e as credenciais `SUPABASE_*` estão configuradas.

Contrato de resiliência: publicar é *best-effort*. O banco é a fonte da
verdade; uma falha de entrega NUNCA pode derrubar um INSERT já efetivado. Por
isso o handler chama `emit()`, que engole qualquer exceção do publisher.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger("app.events")


@dataclass(frozen=True)
class DomainEvent:
    """Evento a transmitir num canal de realtime.

    `channel` é o tópico (ex.: `ticket:<uuid>`), `event` o nome do evento
    (ex.: `ticket.mensagem.created`) e `payload` o corpo JSON-serializável.
    """

    channel: str
    event: str
    payload: dict[str, Any]


class EventPublisher(Protocol):
    """Contrato mínimo. Implementações devem ser best-effort — ver `emit`."""

    def publish(self, event: DomainEvent) -> None: ...


class NoopEventPublisher:
    """Não entrega nada (dev/testes/CI). Loga em debug para rastreabilidade."""

    def publish(self, event: DomainEvent) -> None:
        logger.debug("evento descartado (realtime off): %s @ %s", event.event, event.channel)


class SupabaseEventPublisher:
    """Broadcast no Supabase Realtime via REST (`realtime/v1/api/broadcast`).

    Autentica com a service key (`apikey` + `Authorization: Bearer`). Síncrono
    e com timeout curto (best-effort); para volume alto, trocar por fila/worker.
    Sem dependência nova — usa `urllib` da stdlib.
    """

    def __init__(self, *, base_url: str, service_key: str, timeout: float = 2.0) -> None:
        self._url = base_url.rstrip("/") + "/realtime/v1/api/broadcast"
        self._service_key = service_key
        self._timeout = timeout

    def publish(self, event: DomainEvent) -> None:
        body = json.dumps(
            {"messages": [{"topic": event.channel, "event": event.event, "payload": event.payload}]}
        ).encode()
        req = urllib.request.Request(
            self._url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "apikey": self._service_key,
                "Authorization": f"Bearer {self._service_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            resp.read()


@lru_cache
def _publisher() -> EventPublisher:
    if settings.realtime_enabled and settings.supabase_url and settings.supabase_service_key:
        return SupabaseEventPublisher(
            base_url=settings.supabase_url, service_key=settings.supabase_service_key
        )
    return NoopEventPublisher()


def get_event_publisher() -> EventPublisher:
    """Dependency FastAPI: publisher singleton conforme ambiente.
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _publisher()


def emit(publisher: EventPublisher, event: DomainEvent) -> None:
    """Entrega best-effort: qualquer falha do publisher é logada e engolida — o
    realtime é conveniência, o banco é a fonte da verdade (B4.3)."""
    try:
        publisher.publish(event)
    except Exception:  # noqa: BLE001 — best-effort: nunca derruba o request
        logger.warning(
            "falha ao publicar evento %s @ %s", event.event, event.channel, exc_info=True
        )
