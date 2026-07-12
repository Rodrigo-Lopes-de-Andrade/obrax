"""Fila de processamento dos agentes (`agent.process`) — B10.2.

Mesma dobradiça in-process das outras integrações. O contrato imita o essencial
do Redis Streams + consumer group:

- `enqueue(job)`: enfileira o id da `agent_message` a processar (o corpo e a
  idempotência vivem na tabela `agent_message`, UNIQUE(company_id, message_id)).
- `poll(batch)`: lê um lote (equivalente a `XREADGROUP`).
- `ack(job)`: confirma o processamento (`XACK`).
- `fail(job)`: devolve o job à fila para retry, contando as tentativas; após
  `MAX_ATTEMPTS` (3) o job vira "dead-letter" e sai da fila (equivalente ao
  `XPENDING`/reclaim com backoff 30s/60s/120s do SPRINTS).

Produção: `RedisStreamsAgentQueue` plugaria aqui via `redis.asyncio`. Não
implementado no MVP (sem dependência Redis ainda) — o seam já existe.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

logger = logging.getLogger("app.agent_queue")

MAX_ATTEMPTS = 3
# Backoff (segundos) por tentativa — espelha o SPRINTS (30s/60s/120s).
RETRY_BACKOFF_SECONDS = (30, 60, 120)


@dataclass
class AgentJob:
    """Referência à mensagem a processar. `attempts` conta as entregas."""

    company_id: str
    agent_message_id: str
    attempts: int = 0


class AgentQueue(Protocol):
    def enqueue(self, job: AgentJob) -> None: ...

    def poll(self, *, batch: int) -> list[AgentJob]: ...

    def ack(self, job: AgentJob) -> None: ...

    def fail(self, job: AgentJob) -> None: ...


@dataclass
class InProcessAgentQueue:
    """Fila em memória (por processo). Suficiente para dev/CI e para exercitar o
    fluxo enqueue→worker→ack/retry nos testes; some ao reiniciar o processo."""

    _pending: deque[AgentJob] = field(default_factory=deque)
    dead_letter: list[AgentJob] = field(default_factory=list)

    def enqueue(self, job: AgentJob) -> None:
        self._pending.append(job)

    def poll(self, *, batch: int) -> list[AgentJob]:
        out: list[AgentJob] = []
        while self._pending and len(out) < batch:
            out.append(self._pending.popleft())
        return out

    def ack(self, job: AgentJob) -> None:
        logger.debug("ack job %s (tentativa %d)", job.agent_message_id, job.attempts)

    def fail(self, job: AgentJob) -> None:
        job.attempts += 1
        if job.attempts >= MAX_ATTEMPTS:
            logger.warning("job %s esgotou retries → dead-letter", job.agent_message_id)
            self.dead_letter.append(job)
            return
        self._pending.append(job)

    def __len__(self) -> int:
        return len(self._pending)


@lru_cache
def get_agent_queue() -> InProcessAgentQueue:
    """Fila singleton por processo (dev/CI)."""
    return InProcessAgentQueue()
