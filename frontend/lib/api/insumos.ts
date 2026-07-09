import { api } from "./client";
import type { Insumo, Page } from "./types";

export interface SearchInsumosParams {
  search?: string;
  categoria?: string;
  cursor?: string | null;
  limit?: number;
}

function qs(params: Record<string, string | number | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function searchInsumos(params: SearchInsumosParams = {}): Promise<Page<Insumo>> {
  return api.get(`/api/v1/insumos${qs({ ...params })}`);
}

export function listCategorias(): Promise<{ categorias: string[] }> {
  return api.get(`/api/v1/insumos/categorias`);
}
