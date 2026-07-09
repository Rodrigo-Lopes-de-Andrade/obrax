"""Envio de notificações por e-mail (B4.5).

Ponto de extensão desacoplado do CRUD, na mesma linha de
app/integrations/events.py: o handler monta a mensagem e chama `notify_safe`;
*como* (e se) o e-mail sai é decidido aqui, por ambiente.

- Dev / testes / CI: `NoopNotifier` — não envia, só loga. Mantém o CRUD sem
  acoplamento a provedor/fila.
- Staging / prod: um notifier que enfileira o job `email.send` (arq) ou fala
  com um provedor SMTP/API. Plugável quando essa infra existir (hoje ainda
  não há fila no backend) — seleção por env, sem tocar no chamador.

`EmailMessage` carrega `template` + `context` além de subject/body prontos,
para o provedor de prod renderizar um template customizável (US-20 prep).

Contrato de resiliência: notificar é best-effort — uma falha de envio NUNCA
derruba a operação que a disparou (abrir chamado). Por isso o handler chama
`notify_safe`, que engole qualquer exceção do notifier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

logger = logging.getLogger("app.notifications")


@dataclass(frozen=True)
class EmailMessage:
    """E-mail a enviar. `to` são endereços; `template`/`context` permitem que o
    provedor de prod renderize um template no lugar do `body` pré-montado."""

    to: tuple[str, ...]
    subject: str
    body: str
    template: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


class Notifier(Protocol):
    """Contrato mínimo. Implementações devem ser best-effort — ver `notify_safe`."""

    def send(self, message: EmailMessage) -> None: ...


class NoopNotifier:
    """Não envia (dev/testes/CI). Loga em info para rastreabilidade."""

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "email (noop) para %s: %s",
            ", ".join(message.to) or "(sem destinatários)",
            message.subject,
        )


@lru_cache
def _notifier() -> Notifier:
    # TODO(infra): quando houver fila (arq) ou provedor SMTP/API, selecionar por
    # env (ex.: NOTIFICATIONS_ENABLED + credenciais). Hoje: no-op.
    return NoopNotifier()


def get_notifier() -> Notifier:
    """Dependency FastAPI: notifier singleton conforme ambiente.
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _notifier()


def notify_safe(notifier: Notifier, message: EmailMessage) -> None:
    """Envio best-effort: qualquer falha do notifier é logada e engolida — a
    operação que disparou a notificação nunca é derrubada por ela (B4.5)."""
    if not message.to:
        return
    try:
        notifier.send(message)
    except Exception:  # noqa: BLE001 — best-effort: nunca derruba o request
        logger.warning("falha ao enviar e-mail '%s'", message.subject, exc_info=True)
