import { api } from "./client";
import type {
  Obra,
  ObraCreateInput,
  ObraStatus,
  ObraUpdateInput,
  Page,
} from "./types";

export interface ListObrasParams {
  status?: ObraStatus | null;
  clienteId?: string | null;
  cursor?: string | null;
  limit?: number;
}

function buildQuery(params: ListObrasParams): string {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.clienteId) q.set("cliente_id", params.clienteId);
  if (params.cursor) q.set("cursor", params.cursor);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const listObras = (params: ListObrasParams = {}): Promise<Page<Obra>> =>
  api.get<Page<Obra>>(`/api/v1/obras${buildQuery(params)}`);

export const getObra = (id: string): Promise<Obra> =>
  api.get<Obra>(`/api/v1/obras/${id}`);

export const createObra = (data: ObraCreateInput): Promise<Obra> =>
  api.post<Obra>("/api/v1/obras", data);

export const updateObra = (id: string, data: ObraUpdateInput): Promise<Obra> =>
  api.patch<Obra>(`/api/v1/obras/${id}`, data);

export const deleteObra = (id: string): Promise<void> =>
  api.delete(`/api/v1/obras/${id}`);
