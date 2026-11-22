"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  cancelarDespesa,
  createDespesa,
  createDespesaParcelada,
  estornarDespesa,
  listFasesObra,
  listDespesas,
  pagarDespesa,
  updateDespesa,
  type ListDespesasParams,
} from "@/lib/api/financeiro";
import type {
  DespesaCreate,
  DespesaOut,
  DespesaPage,
  DespesaPagar,
  DespesaParceladaCreate,
  DespesaUpdate,
} from "@/lib/api/types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export const despesaKeys = {
  lists: (obraId: string) => ["financeiro", "despesas", obraId] as const,
  list: (obraId: string, params: ListDespesasParams) =>
    ["financeiro", "despesas", obraId, params] as const,
  fases: (obraId: string) => ["financeiro", "fases", obraId] as const,
  /** Análise orçado × realizado: o realizado/comprometido muda a cada mutação. */
  analise: (obraId: string) => ["financeiro", "orcado-realizado", obraId] as const,
};

/** Fases da obra (RN-F03, E-11): `GET /obras/{id}/fases`, independente da análise e do cronograma. */
export function useFasesObra(obraId: string) {
  return useQuery({
    queryKey: despesaKeys.fases(obraId),
    queryFn: () => listFasesObra(obraId),
  });
}

export function useDespesas(obraId: string, params: ListDespesasParams) {
  return useQuery({
    queryKey: despesaKeys.list(obraId, params),
    queryFn: () => listDespesas(obraId, params),
    placeholderData: keepPreviousData,
  });
}

function listQueries(qc: QueryClient, obraId: string) {
  return qc.getQueryCache().findAll({ queryKey: despesaKeys.lists(obraId) });
}

/** Atualização otimista com a resposta do servidor: cancela fetch em voo (que
 * sobrescreveria a linha com dado velho), troca a linha em todas as listas em cache
 * (some da lista filtrada por status se deixar de casar) e depois revalida. */
async function patchRow(qc: QueryClient, obraId: string, updated: DespesaOut) {
  await qc.cancelQueries({ queryKey: despesaKeys.lists(obraId) });
  for (const q of listQueries(qc, obraId)) {
    const params = (q.queryKey[3] ?? {}) as ListDespesasParams;
    qc.setQueryData<DespesaPage>(q.queryKey, (old) => {
      if (!old) return old;
      const matches = !params.status || params.status === updated.status;
      return {
        ...old,
        items: matches
          ? old.items.map((d) => (d.id === updated.id ? updated : d))
          : old.items.filter((d) => d.id !== updated.id),
      };
    });
  }
  qc.invalidateQueries({ queryKey: despesaKeys.lists(obraId) });
  qc.invalidateQueries({ queryKey: despesaKeys.analise(obraId) });
}

/** Novas despesas entram no topo da 1ª página (e nascem `prevista`, CA-F06.5). */
async function prependRows(qc: QueryClient, obraId: string, created: DespesaOut[]) {
  const ids = new Set(created.map((d) => d.id));
  await qc.cancelQueries({ queryKey: despesaKeys.lists(obraId) });
  for (const q of listQueries(qc, obraId)) {
    const params = (q.queryKey[3] ?? {}) as ListDespesasParams;
    if (params.cursor) continue;
    if (params.status && params.status !== "prevista") continue;
    qc.setQueryData<DespesaPage>(q.queryKey, (old) =>
      old ? { ...old, items: [...created, ...old.items.filter((d) => !ids.has(d.id))] } : old,
    );
  }
  qc.invalidateQueries({ queryKey: despesaKeys.lists(obraId) });
  qc.invalidateQueries({ queryKey: despesaKeys.analise(obraId) });
}

export function useCreateDespesa(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DespesaCreate) => createDespesa(obraId, data),
    onSuccess: async (created) => {
      await prependRows(qc, obraId, [created]);
      toast.success("Despesa lançada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCreateDespesaParcelada(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DespesaParceladaCreate) => createDespesaParcelada(obraId, data),
    onSuccess: async (out) => {
      await prependRows(qc, obraId, out.parcelas);
      toast.success(`${out.parcelas.length} parcelas lançadas`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateDespesa(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DespesaUpdate }) => updateDespesa(id, data),
    onSuccess: async (updated) => {
      await patchRow(qc, obraId, updated);
      toast.success("Despesa atualizada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function usePagarDespesa(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DespesaPagar }) => pagarDespesa(id, data),
    onSuccess: async (updated) => {
      await patchRow(qc, obraId, updated);
      toast.success("Pagamento registrado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCancelarDespesa(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cancelarDespesa(id),
    onSuccess: async (updated) => {
      await patchRow(qc, obraId, updated);
      toast.success("Despesa cancelada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useEstornarDespesa(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => estornarDespesa(id),
    onSuccess: async (updated) => {
      await patchRow(qc, obraId, updated);
      toast.success("Pagamento estornado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
