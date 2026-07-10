import { api } from "./client";
import type { Ocorrencia, OcorrenciaCreateInput, OcorrenciaStatus, Page } from "./types";

export function getOcorrencias(obraId: string): Promise<Page<Ocorrencia>> {
  return api.get(`/api/v1/obras/${obraId}/ocorrencias?limit=100`);
}

export function createOcorrencia(
  obraId: string,
  input: OcorrenciaCreateInput,
): Promise<Ocorrencia> {
  return api.post(`/api/v1/obras/${obraId}/ocorrencias`, input);
}

export function updateOcorrenciaStatus(
  id: string,
  status: OcorrenciaStatus,
): Promise<Ocorrencia> {
  return api.patch(`/api/v1/ocorrencias/${id}`, { status });
}
