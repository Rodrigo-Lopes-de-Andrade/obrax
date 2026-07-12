"""Testes unitários das integrações dos agentes (Módulo 3, Sprint 10).

Cobrem a lógica *pura* (sem banco): HMAC do webhook (B10.1), rate limiter
(B10.1), classificação de intenção (B10.4), copilot (F10.4), retry/dead-letter da
fila (B10.2) e métricas (B10.8). Rodam offline — não dependem de Postgres.

Os testes de API/RLS (webhook→fila→worker→auditoria ponta a ponta) ficam em
test_agentes_api.py e exigem o banco (make test).
"""

from __future__ import annotations

import hashlib
import hmac

from app.integrations.agent_queue import MAX_ATTEMPTS, AgentJob, InProcessAgentQueue
from app.integrations.llm import DeterministicLLM
from app.integrations.uazapi import InProcessRateLimiter, verify_signature
from app.modules.agentes.observability import AgentMetrics
from app.modules.agentes.service import copilot_suggest


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestVerifySignature:
    def test_aceita_assinatura_valida(self) -> None:
        body = b'{"message_id":"1"}'
        assert verify_signature(raw_body=body, signature=_sign(body, "s3cr3t"), secret="s3cr3t")

    def test_aceita_prefixo_sha256(self) -> None:
        body = b"payload"
        sig = "sha256=" + _sign(body, "s3cr3t")
        assert verify_signature(raw_body=body, signature=sig, secret="s3cr3t")

    def test_rejeita_assinatura_errada(self) -> None:
        body = b"payload"
        assert not verify_signature(raw_body=body, signature=_sign(body, "outro"), secret="s3cr3t")

    def test_fail_closed_sem_segredo(self) -> None:
        body = b"payload"
        assert not verify_signature(raw_body=body, signature=_sign(body, ""), secret="")

    def test_fail_closed_sem_assinatura(self) -> None:
        assert not verify_signature(raw_body=b"x", signature=None, secret="s3cr3t")


class TestRateLimiter:
    def test_permite_ate_o_limite_e_bloqueia_depois(self) -> None:
        limiter = InProcessRateLimiter(max_per_minute=3)
        assert [limiter.allow("+551199", now=1000.0) for _ in range(3)] == [True, True, True]
        assert limiter.allow("+551199", now=1000.0) is False

    def test_janela_desliza_apos_60s(self) -> None:
        limiter = InProcessRateLimiter(max_per_minute=1)
        assert limiter.allow("n", now=0.0) is True
        assert limiter.allow("n", now=30.0) is False
        assert limiter.allow("n", now=61.0) is True

    def test_limita_por_numero_independentemente(self) -> None:
        limiter = InProcessRateLimiter(max_per_minute=1)
        assert limiter.allow("a", now=0.0) is True
        assert limiter.allow("b", now=0.0) is True


class TestDeterministicLLM:
    def test_intents(self) -> None:
        llm = DeterministicLLM()
        assert llm.classify_intent("Qual o status da obra?").intent == "consulta_status"
        assert llm.classify_intent("Quanto custou o orçamento?").intent == "consulta_orcamento"
        assert llm.classify_intent("Solicitar 20 sacos de cimento").intent == "criar_compra"
        assert llm.classify_intent("Olá, bom dia").intent == "saudacao"
        assert llm.classify_intent("xyzzy plugh").intent == "desconhecido"

    def test_custo_positivo(self) -> None:
        assert DeterministicLLM().classify_intent("status").cost_cents > 0


class TestCopilot:
    def test_por_palavra_chave(self) -> None:
        itens = copilot_suggest("parede de alvenaria estrutural")
        assert any("Bloco" in i["descricao"] for i in itens)

    def test_fallback_generico(self) -> None:
        itens = copilot_suggest("serviço exótico")
        assert len(itens) == 2
        assert all({"descricao", "unidade", "quantidade"} <= i.keys() for i in itens)


class TestAgentQueue:
    def test_enqueue_poll_ack(self) -> None:
        q = InProcessAgentQueue()
        q.enqueue(AgentJob(company_id="c", agent_message_id="m1"))
        q.enqueue(AgentJob(company_id="c", agent_message_id="m2"))
        jobs = q.poll(batch=10)
        assert [j.agent_message_id for j in jobs] == ["m1", "m2"]
        assert len(q) == 0

    def test_fail_reencaminha_ate_dead_letter(self) -> None:
        q = InProcessAgentQueue()
        job = AgentJob(company_id="c", agent_message_id="m1")
        for _ in range(MAX_ATTEMPTS):
            (j,) = q.poll(batch=1) if len(q) else (job,)
            q.fail(j)
        assert q.dead_letter and q.dead_letter[0].agent_message_id == "m1"
        assert len(q) == 0

    def test_poll_respeita_batch(self) -> None:
        q = InProcessAgentQueue()
        for i in range(5):
            q.enqueue(AgentJob(company_id="c", agent_message_id=str(i)))
        assert len(q.poll(batch=2)) == 2
        assert len(q) == 3


class TestMetrics:
    def test_p95_e_ratio(self) -> None:
        m = AgentMetrics()
        for d in (0.1, 0.2, 0.3, 0.4, 5.0):
            m.observe_duration(d)
        m.observe_interpretation(correct=True)
        m.observe_interpretation(correct=True)
        m.observe_interpretation(correct=False)
        snap = m.snapshot()
        assert snap["agent_response_duration_seconds_p95"] == 5.0
        assert abs(snap["agent_interpretation_correct_ratio"] - 2 / 3) < 1e-9

    def test_defaults_vazios(self) -> None:
        m = AgentMetrics()
        assert m.p95_duration() == 0.0
        assert m.interpretation_ratio() == 1.0
