import { api } from "./client";
import type { RelatorioObrasAtivas, RelatorioOrcamentos } from "./types";

/** Filtro de período (created_at) — datas ISO `YYYY-MM-DD`. */
export interface RelatorioParams {
  from?: string | null;
  to?: string | null;
}

function qs(params: RelatorioParams): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v) sp.set(k, v);
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function getObrasAtivasReport(
  params: RelatorioParams = {},
): Promise<RelatorioObrasAtivas> {
  return api.get(`/api/v1/relatorios/obras-ativas${qs(params)}`);
}

export function getOrcamentosReport(
  params: RelatorioParams = {},
): Promise<RelatorioOrcamentos> {
  return api.get(`/api/v1/relatorios/orcamentos${qs(params)}`);
}
