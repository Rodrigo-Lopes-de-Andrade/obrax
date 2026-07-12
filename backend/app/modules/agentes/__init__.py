"""Módulo 3 — Agentes IA (US-22/23/24, Sprint 10).

Webhook Uazap → fila → orquestrador → subagentes (Orçamento/Compras) → auditoria,
mais os endpoints admin do painel (assistente, auditoria, permissões, copilot,
insights). Integrações externas (LLM, Uazap, fila) são in-process/trocáveis —
ver app/integrations/{llm,uazap,agent_queue}.py.
"""
