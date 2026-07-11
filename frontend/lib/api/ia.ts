import { api } from "./client";
import type {
  AgentChatMessage,
  AgentInteraction,
  AiPermission,
  AiPermissionCreateInput,
  CopilotSuggestInput,
  CopilotSuggestion,
  IaInsights,
  Page,
} from "./types";

/** Módulo 3 — Agentes IA (US-22/23/24). Gated por feature flag
 * `ia-module-enabled` (ver useIaEnabled). */

/* ---- Feature flag ---- */
export function getFeatureFlags(): Promise<Record<string, boolean>> {
  return api.get("/api/v1/feature-flags");
}

/* ---- Assistente IA (F10.1) ---- */
export function getAssistenteThread(): Promise<AgentChatMessage[]> {
  return api.get("/api/v1/ia/assistente/mensagens");
}

/** Envia uma mensagem; o mock LLM devolve a resposta do assistente. */
export function enviarAssistenteMensagem(content: string): Promise<AgentChatMessage> {
  return api.post("/api/v1/ia/assistente/mensagens", { content });
}

/* ---- Auditoria (F10.2) ---- */
export function listarInteracoes(params: {
  obraId?: string | null;
  agent?: string | null;
  cursor?: string | null;
}): Promise<Page<AgentInteraction>> {
  const qs = new URLSearchParams();
  if (params.obraId) qs.set("obra_id", params.obraId);
  if (params.agent) qs.set("agent", params.agent);
  if (params.cursor) qs.set("cursor", params.cursor);
  qs.set("limit", "50");
  return api.get(`/api/v1/ia/interacoes?${qs.toString()}`);
}

export function reverterInteracao(id: string): Promise<AgentInteraction> {
  return api.post(`/api/v1/ia/interacoes/${id}/reverter`, {});
}

/* ---- Permissões IA (F10.3) ---- */
export function listarPermissoes(): Promise<Page<AiPermission>> {
  return api.get("/api/v1/ia/permissoes?limit=50");
}

export function criarPermissao(input: AiPermissionCreateInput): Promise<AiPermission> {
  return api.post("/api/v1/ia/permissoes", input);
}

export function removerPermissao(id: string): Promise<void> {
  return api.delete(`/api/v1/ia/permissoes/${id}`);
}

/* ---- Copilot (F10.4) ---- */
export function copilotSugerir(input: CopilotSuggestInput): Promise<CopilotSuggestion[]> {
  return api.post("/api/v1/ia/copilot/sugerir", input);
}

/* ---- Insights (F10.5) ---- */
export function getIaInsights(): Promise<IaInsights> {
  return api.get("/api/v1/ia/insights");
}
