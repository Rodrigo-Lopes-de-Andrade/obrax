"""Cache TTL para respostas caras e toleráveis a defasagem (B4.4).

O dashboard aceita ~60s de defasagem (docs/SPRINTS.md B4.4: "cache Redis 60s").
Como ainda não há um cache compartilhado (Redis) plugado, o default é um cache
em processo (por worker) com TTL — mesma filosofia de extensão de
app/integrations/events.py: troca-se por uma implementação Redis em
staging/prod sem tocar no chamador. A chave sempre inclui o `company_id`, então
o cache nunca cruza tenant.

Nos testes, sobrescreva `get_dashboard_cache` por `NoopCache` para asserir
sempre o estado atual do banco.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Protocol


class Cache(Protocol):
    """Contrato mínimo de cache chave→valor com expiração implícita."""

    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any) -> None: ...


class NoopCache:
    """Sempre miss — para testes ou quando não se quer cache."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any) -> None:
        return None


class InProcessTTLCache:
    """Cache em memória (por worker) com TTL fixo. `clock` é injetável para
    testes determinísticos (default: relógio monotônico, imune a ajuste de
    hora)."""

    def __init__(self, *, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._clock() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._clock() + self._ttl, value)


# docs/SPRINTS.md B4.4: janela de cache do dashboard.
DASHBOARD_TTL_SECONDS = 60.0
# docs/SPRINTS.md B6.5: relatórios toleram mais defasagem (agregações caras).
RELATORIOS_TTL_SECONDS = 300.0


@lru_cache
def _dashboard_cache() -> Cache:
    return InProcessTTLCache(ttl_seconds=DASHBOARD_TTL_SECONDS)


def get_dashboard_cache() -> Cache:
    """Dependency FastAPI: cache singleton do dashboard (por worker).
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _dashboard_cache()


@lru_cache
def _relatorios_cache() -> Cache:
    return InProcessTTLCache(ttl_seconds=RELATORIOS_TTL_SECONDS)


def get_relatorios_cache() -> Cache:
    """Dependency FastAPI: cache singleton dos relatórios (por worker), TTL 5min.
    Sobrescreva com `app.dependency_overrides` nos testes."""
    return _relatorios_cache()
