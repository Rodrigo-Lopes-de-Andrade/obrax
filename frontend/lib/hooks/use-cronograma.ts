"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  createCronograma,
  getCronograma,
  putAlocacoes,
} from "@/lib/api/financeiro";
import type { AlocacoesPut, CronogramaCreate, CronogramaGradeOut } from "@/lib/api/types";

export const cronogramaKeys = {
  grade: (obraId: string) => ["financeiro", "cronograma", obraId] as const,
};

/** Papéis que editam o cronograma (ESPEC §9, ERRATA E-10). O gestor só lê. */
const PAPEIS_EDITORES = new Set(["owner", "admin", "financeiro"]);
export function podeEditarCronograma(role: string | undefined): boolean {
  return role !== undefined && PAPEIS_EDITORES.has(role);
}

export function mensagemErro(error: unknown): string {
  return error instanceof ApiError ? error.message : "Erro inesperado";
}

/** Cronograma da obra. 404 = obra ainda sem cronograma (não é falha: sem retry). */
export function useCronograma(obraId: string) {
  return useQuery({
    queryKey: cronogramaKeys.grade(obraId),
    queryFn: () => getCronograma(obraId),
    enabled: obraId !== "",
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
}

export function useCriarCronograma(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CronogramaCreate) => createCronograma(obraId, input),
    onSuccess: (grade: CronogramaGradeOut) => {
      qc.setQueryData(cronogramaKeys.grade(obraId), grade);
      toast.success("Cronograma gerado");
    },
  });
}

export function useSalvarAlocacoes(obraId: string, cronogramaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AlocacoesPut) => putAlocacoes(cronogramaId, input),
    onSuccess: (grade: CronogramaGradeOut) => {
      qc.setQueryData(cronogramaKeys.grade(obraId), grade);
      toast.success("Cronograma salvo");
    },
    // A mensagem do backend (fase e diferença, CA-F02.2) fica visível na toolbar.
    // 409 (bloqueou no meio da edição) e 422: recarrega a grade do servidor; no 409 ela vem
    // com `bloqueado_em` e a tela cai em leitura.
    onError: (e) => {
      if (e instanceof ApiError && (e.status === 409 || e.status === 422)) {
        void qc.invalidateQueries({ queryKey: cronogramaKeys.grade(obraId) });
      }
    },
  });
}
