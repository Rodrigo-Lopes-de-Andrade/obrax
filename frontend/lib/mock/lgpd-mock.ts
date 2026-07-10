/**
 * Mock dos pedidos LGPD (US-21). Espelha app/modules/lgpd: o export nasce
 * `concluido` com um link de download fake (TTL 7 dias); o delete nasce
 * `pendente` (anonimização real acontece após 30 dias, no backend).
 */
import type { LgpdRequest, LgpdRequestCreateInput } from "@/lib/api/types";

import { nextId } from "./db";

export const lgpdRequests: LgpdRequest[] = [];

const SETE_DIAS_MS = 7 * 24 * 3_600_000;

export function criarPedidoLgpdMock(input: LgpdRequestCreateInput): LgpdRequest {
  const now = new Date();
  const isExport = input.request_type === "export";
  const id = nextId();
  const req: LgpdRequest = {
    id,
    request_type: input.request_type,
    status: isExport ? "concluido" : "pendente",
    cliente_id: input.cliente_id ?? null,
    created_at: now.toISOString(),
    expires_at: isExport ? new Date(now.getTime() + SETE_DIAS_MS).toISOString() : null,
    processed_at: isExport ? now.toISOString() : null,
    download_url: isExport ? `/_mock/lgpd/${id}.zip` : null,
  };
  lgpdRequests.unshift(req);
  return req;
}

export function listarPedidosLgpdMock(): { items: LgpdRequest[]; next_cursor: null } {
  // O download_url não é repetido na listagem (assinado sob demanda no backend).
  return {
    items: lgpdRequests.map((r) => ({ ...r, download_url: null })),
    next_cursor: null,
  };
}
