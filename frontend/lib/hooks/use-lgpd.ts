"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { criarPedidoLgpd, listarPedidosLgpd } from "@/lib/api/lgpd";
import type { LgpdRequestCreateInput } from "@/lib/api/types";

export const lgpdKeys = {
  requests: ["lgpd", "requests"] as const,
};

export function useLgpdRequests() {
  return useQuery({
    queryKey: lgpdKeys.requests,
    queryFn: () => listarPedidosLgpd(),
  });
}

export function useCriarPedidoLgpd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: LgpdRequestCreateInput) => criarPedidoLgpd(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: lgpdKeys.requests }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível processar o pedido"),
  });
}
