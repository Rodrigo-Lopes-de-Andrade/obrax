"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { createCategoria, listCategorias, updateCategoria } from "@/lib/api/financeiro";
import type { CategoriaCreate, CategoriaUpdate } from "@/lib/api/types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export const categoriaKeys = {
  all: ["financeiro", "categorias"] as const,
  list: (incluirInativas: boolean) => ["financeiro", "categorias", { incluirInativas }] as const,
};

/** Sem `incluirInativas` só vêm as ativas (CA-F05.4: nova despesa não oferece inativa). */
export function useCategorias(incluirInativas = false) {
  return useQuery({
    queryKey: categoriaKeys.list(incluirInativas),
    queryFn: () => listCategorias(incluirInativas),
  });
}

export function useCreateCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CategoriaCreate) => createCategoria(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoriaKeys.all });
      toast.success("Categoria criada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoriaUpdate }) =>
      updateCategoria(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoriaKeys.all });
      toast.success("Categoria atualizada");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
