"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  addPortalMensagem,
  aprovarOrcamento,
  getPortalObra,
  getPortalOrcamento,
  getPortalTickets,
  rejeitarOrcamento,
} from "@/lib/api/portal";
import type { AprovacaoDecisao, MensagemCreateInput, PortalAprovacaoInput } from "@/lib/api/types";

export const portalKeys = {
  obra: (token: string) => ["portal", "obra", token] as const,
  orcamento: (token: string) => ["portal", "orcamento", token] as const,
  tickets: (token: string) => ["portal", "tickets", token] as const,
};

export function usePortalObra(token: string) {
  return useQuery({
    queryKey: portalKeys.obra(token),
    queryFn: () => getPortalObra(token),
    enabled: token !== "",
  });
}

export function usePortalOrcamento(token: string) {
  return useQuery({
    queryKey: portalKeys.orcamento(token),
    queryFn: () => getPortalOrcamento(token),
    enabled: token !== "",
    retry: false, // 404 quando não há orçamento compartilhável — não re-tenta
  });
}

/** Aprovar ou rejeitar o orçamento vigente. */
export function useDecidirOrcamento(token: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { decisao: AprovacaoDecisao; body: PortalAprovacaoInput }) =>
      (vars.decisao === "aprovado" ? aprovarOrcamento : rejeitarOrcamento)(token, vars.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: portalKeys.orcamento(token) }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível registrar"),
  });
}

export function usePortalTickets(token: string) {
  return useQuery({
    queryKey: portalKeys.tickets(token),
    queryFn: () => getPortalTickets(token),
    enabled: token !== "",
  });
}

export function useAddPortalMensagem(token: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { ticketId: string; body: MensagemCreateInput }) =>
      addPortalMensagem(token, vars.ticketId, vars.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: portalKeys.tickets(token) }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível enviar"),
  });
}
