"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  createMensagem,
  createTicket,
  deleteTicket,
  getTicket,
  listMensagens,
  listTickets,
  updateTicketStatus,
  type ListTicketsParams,
} from "@/lib/api/tickets";
import type {
  MensagemCreateInput,
  Page,
  TicketCreateInput,
  TicketMensagem,
  TicketStatus,
  Usuario,
} from "@/lib/api/types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export const ticketKeys = {
  all: ["tickets"] as const,
  lists: () => ["tickets", "list"] as const,
  list: (params: ListTicketsParams) => ["tickets", "list", params] as const,
  detail: (id: string) => ["tickets", "detail", id] as const,
  mensagens: (id: string) => ["tickets", id, "mensagens"] as const,
};

export function useTickets(params: ListTicketsParams) {
  return useQuery({
    queryKey: ticketKeys.list(params),
    queryFn: () => listTickets(params),
    placeholderData: keepPreviousData,
  });
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: () => getTicket(id),
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ obraId, data }: { obraId: string; data: TicketCreateInput }) =>
      createTicket(obraId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ticketKeys.all });
      toast.success("Chamado aberto");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateTicketStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: TicketStatus }) =>
      updateTicketStatus(id, status),
    onSuccess: (updated) => {
      qc.setQueryData(ticketKeys.detail(updated.id), updated);
      qc.invalidateQueries({ queryKey: ticketKeys.lists() });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTicket(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ticketKeys.all });
      toast.success("Chamado excluído");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

/**
 * Histórico do chat. Realtime simulado por reconsulta periódica — com o canal
 * Supabase real, troca-se o `refetchInterval` por
 * `channel.on('postgres_changes') → setQueryData` (F4.5), sem mudar a UI.
 */
export function useMensagens(ticketId: string) {
  return useQuery({
    queryKey: ticketKeys.mensagens(ticketId),
    queryFn: () => listMensagens(ticketId, { limit: 100 }),
    refetchInterval: 4000,
  });
}

/**
 * Envia mensagem com update otimista: aparece na hora (antes do 200), reverte
 * no erro e reconcilia no `onSettled`. A lista vem DESC (mais nova primeiro),
 * então a otimista entra no topo.
 */
export function useCreateMensagem(ticketId: string, me: Usuario | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MensagemCreateInput) => createMensagem(ticketId, data),
    onMutate: async (data) => {
      await qc.cancelQueries({ queryKey: ticketKeys.mensagens(ticketId) });
      const prev = qc.getQueryData<Page<TicketMensagem>>(
        ticketKeys.mensagens(ticketId),
      );
      const optimistic: TicketMensagem = {
        id: `optimistic-${Date.now()}`,
        ticket_id: ticketId,
        author_id: me?.id ?? null,
        content: data.content,
        attachment_paths: data.attachment_paths ?? [],
        created_at: new Date().toISOString(),
      };
      qc.setQueryData<Page<TicketMensagem>>(
        ticketKeys.mensagens(ticketId),
        (old) =>
          old
            ? { ...old, items: [optimistic, ...old.items] }
            : { items: [optimistic], next_cursor: null },
      );
      return { prev };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(ticketKeys.mensagens(ticketId), ctx.prev);
      toast.error(errorMessage(error));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ticketKeys.mensagens(ticketId) });
    },
  });
}
