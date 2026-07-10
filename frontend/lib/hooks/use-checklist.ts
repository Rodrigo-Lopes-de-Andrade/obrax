"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { createChecklistItem, getChecklist } from "@/lib/api/checklist";

export const checklistKeys = {
  all: ["checklist"] as const,
  list: (obraId: string) => ["checklist", obraId] as const,
};

export function useChecklist(obraId: string) {
  return useQuery({
    queryKey: checklistKeys.list(obraId),
    queryFn: () => getChecklist(obraId),
    enabled: obraId !== "",
  });
}

/** Adição de item é online (o gestor define o checklist; o campo marca). Offline
 * a mutação falha com aviso — o fluxo offline principal é o toggle. */
export function useAddChecklistItem(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (titulo: string) => createChecklistItem(obraId, { titulo }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: checklistKeys.list(obraId) });
    },
    onError: (error) =>
      toast.error(
        error instanceof ApiError ? error.message : "Sem conexão — tente novamente online",
      ),
  });
}
