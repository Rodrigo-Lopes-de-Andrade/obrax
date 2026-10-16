import { api } from "./client";
import type { Cliente, ClienteCreateInput, ClienteUpdateInput, Page } from "./types";

export interface ListClientesParams {
  search?: string | null;
  cursor?: string | null;
  limit?: number;
}

function buildQuery(params: ListClientesParams): string {
  const q = new URLSearchParams();
  if (params.search) q.set("search", params.search);
  if (params.cursor) q.set("cursor", params.cursor);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const listClientes = (
  params: ListClientesParams = {},
): Promise<Page<Cliente>> =>
  api.get<Page<Cliente>>(`/api/v1/clientes${buildQuery(params)}`);

export const createCliente = (data: ClienteCreateInput): Promise<Cliente> =>
  api.post<Cliente>("/api/v1/clientes", data);

export const updateCliente = (id: string, data: ClienteUpdateInput): Promise<Cliente> =>
  api.patch<Cliente>(`/api/v1/clientes/${id}`, data);

export const deleteCliente = (id: string): Promise<void> =>
  api.delete(`/api/v1/clientes/${id}`);
