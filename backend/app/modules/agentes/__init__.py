"""Módulo 3 — Agentes IA (US-22/23/24, Sprint 10).

Webhook Uazapi → fila → orquestrador → subagentes (Orçamento/Compras) → auditoria,
mais os endpoints admin do painel (assistente, auditoria, permissões, copilot,
insights). Integrações externas (LLM, Uazapi, fila) são in-process/trocáveis —
ver app/integrations/{llm,uazapi,agent_queue}.py.
"""
