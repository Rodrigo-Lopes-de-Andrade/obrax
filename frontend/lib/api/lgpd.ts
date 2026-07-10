import { api } from "./client";
import type { LgpdRequest, LgpdRequestCreateInput, Page } from "./types";

/** Pedidos LGPD (US-21) — owner/admin. O export monta o ZIP e devolve o pedido
 * já concluído com a URL de download; o delete registra o pedido pendente. */

export function criarPedidoLgpd(input: LgpdRequestCreateInput): Promise<LgpdRequest> {
  return api.post("/api/v1/lgpd/requests", input);
}

export function listarPedidosLgpd(): Promise<Page<LgpdRequest>> {
  return api.get("/api/v1/lgpd/requests?limit=50");
}
