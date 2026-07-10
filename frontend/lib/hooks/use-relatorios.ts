"use client";

import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getObrasAtivasReport,
  getOrcamentosReport,
  type RelatorioParams,
} from "@/lib/api/relatorios";

export const relatorioKeys = {
  all: ["relatorios"] as const,
  obrasAtivas: (p: RelatorioParams) => ["relatorios", "obras-ativas", p] as const,
  orcamentos: (p: RelatorioParams) => ["relatorios", "orcamentos", p] as const,
};

export function useObrasAtivasReport(params: RelatorioParams) {
  return useQuery({
    queryKey: relatorioKeys.obrasAtivas(params),
    queryFn: () => getObrasAtivasReport(params),
    placeholderData: keepPreviousData,
  });
}

export function useOrcamentosReport(params: RelatorioParams) {
  return useQuery({
    queryKey: relatorioKeys.orcamentos(params),
    queryFn: () => getOrcamentosReport(params),
    placeholderData: keepPreviousData,
  });
}

/** Refresh manual: invalida todos os relatórios (o cache de 5min do backend
 * ainda vale — aqui forçamos a releitura no cliente). */
export function useRefreshRelatorios() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: relatorioKeys.all });
}
