import { api } from "./client";
import type { Membro, MembroCreateInput, Page, Usuario } from "./types";

export interface ListMembrosParams {
  cursor?: string | null;
  limit?: number;
}

function buildQuery(params: ListMembrosParams): string {
  const q = new URLSearchParams();
  if (params.cursor) q.set("cursor", params.cursor);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const listMembros = (
  obraId: string,
  params: ListMembrosParams = {},
): Promise<Page<Membro>> =>
  api.get<Page<Membro>>(`/api/v1/obras/${obraId}/membros${buildQuery(params)}`);

export const addMembro = (
  obraId: string,
  data: MembroCreateInput,
): Promise<Membro> =>
  api.post<Membro>(`/api/v1/obras/${obraId}/membros`, data);

export const removeMembro = (obraId: string, userId: string): Promise<void> =>
  api.delete(`/api/v1/obras/${obraId}/membros/${userId}`);

/**
 * Busca usuários do tenant para o seletor de "adicionar membro". Endpoint de
 * listagem de usuários ainda não existe no backend (fora do escopo de B3.6);
 * por ora só o mock MSW responde — ao ligar o backend real, criar
 * GET /api/v1/usuarios.
 */
export const searchUsuarios = (search: string): Promise<Page<Usuario>> => {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return api.get<Page<Usuario>>(`/api/v1/usuarios${qs}`);
};
