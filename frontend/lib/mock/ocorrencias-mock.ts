/**
 * Mock das ocorrências de campo (B8.4, US-18). Espelha gestao/ocorrencias:
 * foto obrigatória (photo_ids vinculadas via photo.ocorrencia_id, escopadas pela
 * obra), GPS opcional e status aberto/resolvido.
 */
import type { Ocorrencia, OcorrenciaCreateInput } from "@/lib/api/types";
import { nextId, obras } from "./db";
import { photos } from "./fotos-mock";

export const ocorrencias: Ocorrencia[] = [];

export class OcorrenciasMockError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

export function createOcorrenciaMock(obraId: string, input: OcorrenciaCreateInput): Ocorrencia {
  if (!obras.some((o) => o.id === obraId)) throw new OcorrenciasMockError(422, "obra não encontrada");
  if (!input.titulo?.trim()) throw new OcorrenciasMockError(422, "título obrigatório");
  const ids = Array.from(new Set(input.photo_ids ?? []));
  if (ids.length === 0) throw new OcorrenciasMockError(422, "foto obrigatória");

  const ocorrenciaId = nextId();
  // Só vincula fotos da obra ainda livres — igual ao UPDATE escopado do backend.
  const alvo = photos.filter(
    (p) => ids.includes(p.id) && p.obra_id === obraId && p.ocorrencia_id === null,
  );
  if (alvo.length !== ids.length) {
    throw new OcorrenciasMockError(
      422,
      "foto inválida: inexistente, de outra obra ou já vinculada",
    );
  }
  alvo.forEach((p) => (p.ocorrencia_id = ocorrenciaId));

  const oc: Ocorrencia = {
    id: ocorrenciaId,
    obra_id: obraId,
    titulo: input.titulo.trim(),
    descricao: input.descricao?.trim() || null,
    status: "aberto",
    gps_lat: input.gps_lat ?? null,
    gps_lng: input.gps_lng ?? null,
    photo_ids: alvo.map((p) => p.id).sort(),
    created_at: nowIso(),
  };
  ocorrencias.push(oc);
  return oc;
}

export function listOcorrenciasMock(obraId: string): { items: Ocorrencia[]; next_cursor: null } {
  if (!obras.some((o) => o.id === obraId)) throw new OcorrenciasMockError(404, "obra não encontrada");
  const rows = [...ocorrencias]
    .filter((o) => o.obra_id === obraId)
    .sort((a, b) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0));
  return { items: rows, next_cursor: null };
}

export function updateOcorrenciaStatusMock(id: string, status: "aberto" | "resolvido"): Ocorrencia {
  const oc = ocorrencias.find((o) => o.id === id);
  if (!oc) throw new OcorrenciasMockError(404, "ocorrência não encontrada");
  oc.status = status;
  return oc;
}
