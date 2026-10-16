"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  createCliente,
  deleteCliente,
  listClientes,
  updateCliente,
  type ListClientesParams,
} from "@/lib/api/clientes";
import type { ClienteCreateInput, ClienteUpdateInput } from "@/lib/api/types";

export const clientesKeys = {
  all: ["clientes"] as const,
  list: (params: ListClientesParams) => ["clientes", "list", params] as const,
};

/** Lista de clientes para o select do formulário e o mapa id→nome da tabela. */
export function useClientes() {
  return useQuery({
    queryKey: clientesKeys.list({ limit: 100 }),
    queryFn: () => listClientes({ limit: 100 }),
    staleTime: 60_000,
  });
}

/** Lista paginada/filtrada da tela de Clientes. */
export function useClientesPage(params: ListClientesParams) {
  return useQuery({
    queryKey: clientesKeys.list(params),
    queryFn: () => listClientes(params),
    placeholderData: keepPreviousData,
  });
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

export function useCreateCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ClienteCreateInput) => createCliente(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clientesKeys.all });
      toast.success("Cliente cadastrado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ClienteUpdateInput }) => updateCliente(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clientesKeys.all });
      toast.success("Cliente atualizado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCliente(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clientesKeys.all });
      toast.success("Cliente excluído");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
