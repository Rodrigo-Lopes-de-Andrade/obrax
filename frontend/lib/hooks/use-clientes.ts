"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { createCliente, listClientes } from "@/lib/api/clientes";
import type { ClienteCreateInput } from "@/lib/api/types";

/** Lista de clientes para o select do formulário e o mapa id→nome da tabela. */
export function useClientes() {
  return useQuery({
    queryKey: ["clientes", "list"],
    queryFn: () => listClientes({ limit: 100 }),
    staleTime: 60_000,
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
      qc.invalidateQueries({ queryKey: ["clientes"] });
      toast.success("Cliente criado");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
