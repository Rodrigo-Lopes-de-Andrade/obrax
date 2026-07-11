"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  copilotSugerir,
  criarPermissao,
  enviarAssistenteMensagem,
  getAssistenteThread,
  getFeatureFlags,
  getIaInsights,
  listarInteracoes,
  listarPermissoes,
  removerPermissao,
  reverterInteracao,
} from "@/lib/api/ia";
import type { AiPermissionCreateInput, CopilotSuggestInput } from "@/lib/api/types";

export const iaKeys = {
  flags: ["ia", "flags"] as const,
  thread: ["ia", "assistente", "thread"] as const,
  interacoes: (obraId: string | null, agent: string | null) =>
    ["ia", "interacoes", obraId, agent] as const,
  permissoes: ["ia", "permissoes"] as const,
  insights: ["ia", "insights"] as const,
};

/** Flag `ia-module-enabled` (US-24, tier Pro/Enterprise). Enquanto carrega,
 * assume habilitado para não piscar o bloqueio. */
export function useIaEnabled(): boolean {
  const { data } = useQuery({
    queryKey: iaKeys.flags,
    queryFn: getFeatureFlags,
    staleTime: 5 * 60_000,
  });
  return data?.["ia-module-enabled"] ?? true;
}

/* ---- Assistente ---- */
export function useAssistenteThread() {
  return useQuery({ queryKey: iaKeys.thread, queryFn: getAssistenteThread });
}

export function useEnviarAssistenteMensagem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => enviarAssistenteMensagem(content),
    onSuccess: () => qc.invalidateQueries({ queryKey: iaKeys.thread }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível enviar"),
  });
}

/* ---- Auditoria ---- */
export function useInteracoes(obraId: string | null, agent: string | null) {
  return useQuery({
    queryKey: iaKeys.interacoes(obraId, agent),
    queryFn: () => listarInteracoes({ obraId, agent }),
  });
}

export function useReverterInteracao(obraId: string | null, agent: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reverterInteracao(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: iaKeys.interacoes(obraId, agent) });
      qc.invalidateQueries({ queryKey: iaKeys.insights });
      toast.success("Ação revertida");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível reverter"),
  });
}

/* ---- Permissões ---- */
export function usePermissoes() {
  return useQuery({ queryKey: iaKeys.permissoes, queryFn: listarPermissoes });
}

export function useCriarPermissao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AiPermissionCreateInput) => criarPermissao(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: iaKeys.permissoes });
      toast.success("Permissão salva");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível salvar"),
  });
}

export function useRemoverPermissao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => removerPermissao(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: iaKeys.permissoes }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível remover"),
  });
}

/* ---- Copilot ---- */
export function useCopilotSugerir() {
  return useMutation({
    mutationFn: (input: CopilotSuggestInput) => copilotSugerir(input),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível sugerir"),
  });
}

/* ---- Insights ---- */
export function useIaInsights() {
  return useQuery({
    queryKey: iaKeys.insights,
    queryFn: getIaInsights,
    staleTime: 5 * 60_000,
  });
}
