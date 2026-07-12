"""Abstração de LLM para os agentes (Módulo 3, B10.3/B10.4).

Mesma filosofia de `integrations/events.py` e `integrations/cache.py`: o chamador
depende de um `Protocol`, e *qual* implementação roda é decidido por ambiente,
sem tocar no orquestrador.

- Dev / testes / CI: `DeterministicLLM` — classifica a intenção e gera respostas
  por heurística de palavra-chave. Sem rede, sem chave, sem custo: os testes de
  interpretação (B10.4) rodam offline e são reprodutíveis.
- Staging / prod: `ClaudeLLM` (primário Claude Sonnet, docs/CLAUDE.md) seria
  plugado aqui via httpx, com fallback GPT-4o. Não implementado no MVP para não
  introduzir dependência/chave; o seam (`get_llm_client`) já existe.

O custo estimado por interação (`cost_cents`) é devolvido junto para alimentar o
enforcement de limite de gasto (B10.7) sem depender do provedor real.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol

# Intenções que o roteador do orquestrador conhece (B10.3).
Intent = Literal[
    "consulta_status",
    "consulta_orcamento",
    "criar_compra",
    "saudacao",
    "desconhecido",
]


@dataclass(frozen=True)
class LLMResult:
    """Saída da classificação de intenção + custo estimado (centavos)."""

    intent: Intent
    cost_cents: int


class LLMClient(Protocol):
    """Contrato mínimo consumido pelo orquestrador."""

    def classify_intent(self, message: str) -> LLMResult: ...

    def compose(self, prompt: str) -> str: ...


_STATUS_KWS = ("status", "andamento", "progresso", "prazo", "avanço", "avanco")
_ORCAMENTO_KWS = ("orçament", "orcament", "custo", "valor", "preço", "preco", "quanto")
_COMPRA_KWS = ("compra", "comprar", "solicit", "material", "insumo", "cimento", "pedir")
_SAUDACAO_KWS = ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "ajuda")


class DeterministicLLM:
    """Classificador por palavra-chave (dev/testes). A precisão é suficiente
    para o MVP (SPRINTS B10.4: ≥90% no conjunto de comandos previstos)."""

    def classify_intent(self, message: str) -> LLMResult:
        q = message.lower()
        if any(k in q for k in _COMPRA_KWS):
            return LLMResult(intent="criar_compra", cost_cents=11)
        if any(k in q for k in _ORCAMENTO_KWS):
            return LLMResult(intent="consulta_orcamento", cost_cents=5)
        if any(k in q for k in _STATUS_KWS):
            return LLMResult(intent="consulta_status", cost_cents=4)
        if any(k in q for k in _SAUDACAO_KWS):
            return LLMResult(intent="saudacao", cost_cents=1)
        return LLMResult(intent="desconhecido", cost_cents=2)

    def compose(self, prompt: str) -> str:
        # No modo determinístico o "prompt" já é a resposta pronta montada pelo
        # subagente (não há geração livre). Mantido para paridade de contrato.
        return prompt


@lru_cache
def _client() -> LLMClient:
    # Sem provedor real no MVP; sempre determinístico. O seam permanece para
    # plugar ClaudeLLM/GPT4o em staging/prod (settings.anthropic_api_key etc.).
    return DeterministicLLM()


def get_llm_client() -> LLMClient:
    """Dependency FastAPI: cliente LLM conforme ambiente. Sobrescreva com
    `app.dependency_overrides` nos testes."""
    return _client()
