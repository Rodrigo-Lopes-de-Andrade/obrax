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
  bulkCreateItens,
  createOrcamento,
  deleteItemTree,
  deleteOrcamento,
  duplicateItem,
  gerarPdf,
  getCurvaAbc,
  getEapTree,
  getOrcamento,
  getPdfStatus,
  importErros,
  importPlanilha,
  listOrcamentos,
  reorderItens,
  setPrecificacao,
  updateItem,
  updateOrcamentoStatus,
  type ListOrcamentosParams,
} from "@/lib/api/orcamentos";
import type {
  EapTree,
  ItemCreateInput,
  ItemUpdateInput,
  OrcamentoCreateInput,
  OrcamentoStatus,
  ReorderItemInput,
} from "@/lib/api/types";

export const orcamentoKeys = {
  all: ["orcamentos"] as const,
  list: (params: ListOrcamentosParams) => ["orcamentos", "list", params] as const,
  detail: (id: string) => ["orcamentos", "detail", id] as const,
  tree: (versaoId: string) => ["orcamentos", "tree", versaoId] as const,
  curva: (id: string) => ["orcamentos", "curva-abc", id] as const,
  pdf: (id: string) => ["orcamentos", "pdf", id] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export function useOrcamentos(params: ListOrcamentosParams) {
  return useQuery({
    queryKey: orcamentoKeys.list(params),
    queryFn: () => listOrcamentos(params),
    placeholderData: keepPreviousData,
  });
}

export function useOrcamento(id: string) {
  return useQuery({
    queryKey: orcamentoKeys.detail(id),
    queryFn: () => getOrcamento(id),
    enabled: id !== "",
  });
}

export function useEapTree(versaoId: string) {
  return useQuery({
    queryKey: orcamentoKeys.tree(versaoId),
    queryFn: () => getEapTree(versaoId),
    enabled: versaoId !== "",
  });
}

export function useCurvaAbc(orcamentoId: string) {
  return useQuery({
    queryKey: orcamentoKeys.curva(orcamentoId),
    queryFn: () => getCurvaAbc(orcamentoId),
    enabled: orcamentoId !== "",
  });
}

/** Status do PDF (URL de download). Desligado até o usuário abrir o painel;
 * 404 (ainda não gerado) não deve insistir em retry. */
export function usePdfStatus(orcamentoId: string, enabled: boolean) {
  return useQuery({
    queryKey: orcamentoKeys.pdf(orcamentoId),
    queryFn: () => getPdfStatus(orcamentoId),
    enabled: enabled && orcamentoId !== "",
    retry: false,
  });
}

export function useGerarPdf(orcamentoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => gerarPdf(orcamentoId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orcamentoKeys.pdf(orcamentoId) });
      toast.success("PDF gerado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCreateOrcamento(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OrcamentoCreateInput) => createOrcamento(obraId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orcamentoKeys.all });
      toast.success("Orçamento criado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateOrcamentoStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: OrcamentoStatus }) =>
      updateOrcamentoStatus(id, status),
    onSuccess: (detail) => {
      qc.setQueryData(orcamentoKeys.detail(detail.id), detail);
      qc.invalidateQueries({ queryKey: orcamentoKeys.all });
      toast.success("Status atualizado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteOrcamento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteOrcamento(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orcamentoKeys.all });
      toast.success("Orçamento excluído");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

/** Aplica a árvore recalculada devolvida por uma mutação de itens ao cache. */
function useTreeMutation<TVars>(
  versaoId: string,
  mutationFn: (vars: TVars) => Promise<EapTree>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (tree) => {
      qc.setQueryData(orcamentoKeys.tree(versaoId), tree);
      // Os agregados da versão mudaram → atualiza detalhe/listagem.
      qc.invalidateQueries({ queryKey: orcamentoKeys.all });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useBulkCreateItens(versaoId: string) {
  return useTreeMutation(versaoId, (itens: ItemCreateInput[]) =>
    bulkCreateItens(versaoId, itens),
  );
}

export function useUpdateItem(versaoId: string) {
  return useTreeMutation(versaoId, ({ id, patch }: { id: string; patch: ItemUpdateInput }) =>
    updateItem(id, patch),
  );
}

export function useDeleteItem(versaoId: string) {
  return useTreeMutation(versaoId, (itemId: string) => deleteItemTree(itemId));
}

export function useDuplicateItem(versaoId: string) {
  return useTreeMutation(versaoId, (itemId: string) => duplicateItem(itemId));
}

export function useReorderItens(versaoId: string) {
  return useTreeMutation(versaoId, (itens: ReorderItemInput[]) =>
    reorderItens(versaoId, itens),
  );
}

export function useSetPrecificacao(versaoId: string) {
  return useTreeMutation(
    versaoId,
    ({ markup_global, taxa_adm }: { markup_global: string; taxa_adm: string }) =>
      setPrecificacao(versaoId, { markup_global, taxa_adm }),
  );
}

export function useImportPlanilha(versaoId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importPlanilha(versaoId, file),
    onSuccess: (tree) => {
      qc.setQueryData(orcamentoKeys.tree(versaoId), tree);
      qc.invalidateQueries({ queryKey: orcamentoKeys.all });
      toast.success("Planilha importada");
    },
    // Erros linha-a-linha são tratados pelo componente (importErros).
  });
}

export { importErros };
