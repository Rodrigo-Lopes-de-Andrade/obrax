"""Integração com o Uazap (gateway WhatsApp) — B10.1.

Duas responsabilidades:

1. **Verificação do webhook** (`verify_signature`): valida o HMAC-SHA256 do corpo
   cru com o segredo compartilhado (`UAZAP_WEBHOOK_SECRET`). Comparação em tempo
   constante (`hmac.compare_digest`). Fail-closed: sem segredo configurado, ou
   assinatura ausente/errada → inválido.

2. **Envio de mensagens** (`UazapClient`): mesma dobradiça de `events.py` —
   `NoopUazapClient` em dev/CI (não faz rede; loga) e `HttpUazapClient` (httpx)
   em staging/prod quando `UAZAP_BASE_URL`/`UAZAP_TOKEN` estão setados.

O rate limit por número (B10.1: 10/min) é um token-bucket em processo
(`InProcessRateLimiter`) — trocável por Redis em produção, como o resto das
integrações in-process (cache/events/queue).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections import defaultdict, deque
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger("app.uazap")


def verify_signature(*, raw_body: bytes, signature: str | None, secret: str) -> bool:
    """HMAC-SHA256 do corpo cru == assinatura enviada (hex). Fail-closed."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Aceita tanto "sha256=<hex>" quanto "<hex>" puro.
    provided = signature.split("=", 1)[1] if signature.startswith("sha256=") else signature
    return hmac.compare_digest(expected, provided)


class UazapClient(Protocol):
    def send_text(self, *, to: str, text: str) -> None: ...


class NoopUazapClient:
    """Não envia nada (dev/testes/CI). Loga para rastreabilidade."""

    def send_text(self, *, to: str, text: str) -> None:
        logger.debug("uazap send (noop) -> %s: %s", to, text)


class HttpUazapClient:
    """Envio real via REST do Uazap (staging/prod). Best-effort e timeout curto:
    uma falha de envio não pode derrubar o processamento já auditado."""

    def __init__(self, *, base_url: str, token: str, timeout: float = 5.0) -> None:
        self._url = base_url.rstrip("/") + "/send/text"
        self._token = token
        self._timeout = timeout

    def send_text(self, *, to: str, text: str) -> None:
        try:
            httpx.post(
                self._url,
                json={"number": to, "text": text},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError:
            logger.warning("falha ao enviar mensagem Uazap para %s", to, exc_info=True)


@lru_cache
def _client() -> UazapClient:
    if settings.uazap_base_url and settings.uazap_token:
        return HttpUazapClient(base_url=settings.uazap_base_url, token=settings.uazap_token)
    return NoopUazapClient()


def get_uazap_client() -> UazapClient:
    """Dependency FastAPI: cliente Uazap conforme ambiente."""
    return _client()


class InProcessRateLimiter:
    """Token-bucket simples por chave (número). Janela deslizante de 60s.

    Em processo (por worker) — para o rate limit global de produção, trocar por
    Redis. Determinístico via injeção de `now` nos testes.
    """

    def __init__(self, *, max_per_minute: int = 10) -> None:
        self._max = max_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, now: float) -> bool:
        window = self._hits[key]
        limit = now - 60.0
        while window and window[0] < limit:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(now)
        return True


@lru_cache
def get_rate_limiter() -> InProcessRateLimiter:
    """Rate limiter singleton (10/min por número, B10.1)."""
    return InProcessRateLimiter(max_per_minute=10)
