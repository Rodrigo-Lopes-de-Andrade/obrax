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
  createObra,
  deleteObra,
  listObras,
  updateObra,
  type ListObrasParams,
} from "@/lib/api/obras";
import type { ObraCreateInput, ObraUpdateInput } from "@/lib/api/types";

export const obrasKeys = {
  all: ["obras"] as const,
  list: (params: ListObrasParams) => ["obras", "list", params] as const,
};

export function useObras(params: ListObrasParams) {
  return useQuery({
    queryKey: obrasKeys.list(params),
    queryFn: () => listObras(params),
    // Mantém a página atual visível durante o refetch (paginação/filtro suaves).
    placeholderData: keepPreviousData,
  });
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export function useCreateObra() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ObraCreateInput) => createObra(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obrasKeys.all });
      toast.success("Obra criada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateObra() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ObraUpdateInput }) =>
      updateObra(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obrasKeys.all });
      toast.success("Obra atualizada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteObra() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteObra(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: obrasKeys.all });
      toast.success("Obra excluída");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
