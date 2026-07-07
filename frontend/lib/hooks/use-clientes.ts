"use client";

import { useQuery } from "@tanstack/react-query";

import { listClientes } from "@/lib/api/clientes";

/** Lista de clientes para o select do formulário e o mapa id→nome da tabela. */
export function useClientes() {
  return useQuery({
    queryKey: ["clientes", "list"],
    queryFn: () => listClientes({ limit: 100 }),
    staleTime: 60_000,
  });
}
