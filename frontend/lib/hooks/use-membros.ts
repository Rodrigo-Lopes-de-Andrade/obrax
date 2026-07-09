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
  addMembro,
  listMembros,
  removeMembro,
  searchUsuarios,
  type ListMembrosParams,
} from "@/lib/api/membros";
import type { MembroCreateInput } from "@/lib/api/types";

export const membrosKeys = {
  all: (obraId: string) => ["membros", obraId] as const,
  list: (obraId: string, params: ListMembrosParams) =>
    ["membros", obraId, "list", params] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export function useMembros(obraId: string, params: ListMembrosParams = {}) {
  return useQuery({
    queryKey: membrosKeys.list(obraId, params),
    queryFn: () => listMembros(obraId, params),
    placeholderData: keepPreviousData,
  });
}

export function useSearchUsuarios(search: string) {
  return useQuery({
    queryKey: ["usuarios", "search", search] as const,
    queryFn: () => searchUsuarios(search),
    placeholderData: keepPreviousData,
  });
}

export function useAddMembro(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MembroCreateInput) => addMembro(obraId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: membrosKeys.all(obraId) });
      toast.success("Membro adicionado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useRemoveMembro(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeMembro(obraId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: membrosKeys.all(obraId) });
      toast.success("Membro removido");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
