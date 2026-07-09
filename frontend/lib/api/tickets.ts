import { api } from "./client";
import type {
  MensagemCreateInput,
  Page,
  Ticket,
  TicketCreateInput,
  TicketMensagem,
  TicketStatus,
} from "./types";

export interface ListTicketsParams {
  obra_id?: string | null;
  status?: TicketStatus | null;
  /** Busca por título (extensão do mock; o backend ganhará o parâmetro). */
  search?: string | null;
  cursor?: string | null;
  limit?: number;
}

function buildQuery(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  }
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const listTickets = (params: ListTicketsParams = {}): Promise<Page<Ticket>> =>
  api.get<Page<Ticket>>(`/api/v1/tickets${buildQuery({ ...params })}`);

export const getTicket = (id: string): Promise<Ticket> =>
  api.get<Ticket>(`/api/v1/tickets/${id}`);

export const createTicket = (obraId: string, data: TicketCreateInput): Promise<Ticket> =>
  api.post<Ticket>(`/api/v1/obras/${obraId}/tickets`, data);

export const updateTicketStatus = (id: string, status: TicketStatus): Promise<Ticket> =>
  api.patch<Ticket>(`/api/v1/tickets/${id}/status`, { status });

export const deleteTicket = (id: string): Promise<void> =>
  api.delete(`/api/v1/tickets/${id}`);

export interface ListMensagensParams {
  cursor?: string | null;
  limit?: number;
}

export const listMensagens = (
  ticketId: string,
  params: ListMensagensParams = {},
): Promise<Page<TicketMensagem>> =>
  api.get<Page<TicketMensagem>>(
    `/api/v1/tickets/${ticketId}/mensagens${buildQuery({ ...params })}`,
  );

export const createMensagem = (
  ticketId: string,
  data: MensagemCreateInput,
): Promise<TicketMensagem> =>
  api.post<TicketMensagem>(`/api/v1/tickets/${ticketId}/mensagens`, data);
