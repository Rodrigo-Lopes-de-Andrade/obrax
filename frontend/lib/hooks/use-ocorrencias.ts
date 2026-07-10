"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import {
  createOcorrencia,
  getOcorrencias,
  updateOcorrenciaStatus,
} from "@/lib/api/ocorrencias";
import type { OcorrenciaCreateInput, OcorrenciaStatus } from "@/lib/api/types";

export const ocorrenciasKeys = {
  all: ["ocorrencias"] as const,
  list: (obraId: string) => ["ocorrencias", obraId] as const,
};

export function useOcorrencias(obraId: string) {
  return useQuery({
    queryKey: ocorrenciasKeys.list(obraId),
    queryFn: () => getOcorrencias(obraId),
    enabled: obraId !== "",
  });
}

/** Registrar ocorrência é online: a foto (evidência) precisa subir e virar
 * photo_id no servidor antes do POST. Offline, avisa e mantém o rascunho. */
export function useCreateOcorrencia(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: OcorrenciaCreateInput) => createOcorrencia(obraId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ocorrenciasKeys.list(obraId) });
    },
    onError: (error) =>
      toast.error(
        error instanceof ApiError ? error.message : "Sem conexão — registre quando houver rede",
      ),
  });
}

export function useUpdateOcorrenciaStatus(obraId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; status: OcorrenciaStatus }) =>
      updateOcorrenciaStatus(vars.id, vars.status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ocorrenciasKeys.list(obraId) });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Não foi possível atualizar"),
  });
}
