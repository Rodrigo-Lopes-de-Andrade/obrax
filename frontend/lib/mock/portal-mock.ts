/**
 * Mock do portal do cliente (US-19/US-20). Espelha app/modules/portal: resolve o
 * `token` para uma obra, monta a timeline read-only (docs visíveis + fotos) e o
 * orçamento vigente para aprovar. Sem números financeiros internos.
 *
 * No mock o token é o próprio `obra.id` (o mint devolve assim); um token
 * desconhecido cai na última obra semeada (que tem docs+fotos+orçamento) para
 * o portal abrir direto em /obra/qualquer-coisa durante a demo.
 */
import type {
  MensagemCreateInput,
  PortalObra,
  PortalOrcamento,
  PortalTicket,
  TicketMensagem,
} from "@/lib/api/types";

import { documentos, mensagens, nextId, obras, tickets } from "./db";
import { listPhotosMock } from "./fotos-mock";
import { orcamentos, updateStatus, versoes } from "./orcamento-mock";

/** Razão social da construtora (tenant) — branding do portal. */
export const PORTAL_CONSTRUTORA = "Construtora Aurora Engenharia";

/** Status de orçamento que o cliente pode ver (saiu do rascunho). */
const COMPARTILHAVEL = new Set(["aguardando_aprovacao", "aprovado", "rejeitado"]);

/** Decisão registrada por orçamento (comentário/assinatura + carimbo). */
const decisoes = new Map<string, { decisao: "aprovado" | "rejeitado"; decidido_em: string }>();

export class PortalMockError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "PortalMockError";
  }
}

function resolveObra(token: string) {
  const obra = obras.find((o) => o.id === token) ?? obras[obras.length - 1];
  if (!obra) throw new PortalMockError(404, "obra não encontrada");
  return obra;
}

export function getPortalObraMock(token: string): PortalObra {
  const obra = resolveObra(token);
  const docs = documentos
    .filter((d) => d.obra_id === obra.id && d.visivel_cliente && d.confirmed)
    .sort((a, b) => b.id.localeCompare(a.id))
    .map((d) => ({
      id: d.id,
      nome: d.nome,
      tipo: d.tipo,
      categoria: d.categoria,
      created_at: d.created_at,
      download_url: `/_mock/storage/${d.id}`,
    }));
  const fotos = listPhotosMock(obra.id).items.map((p) => ({
    id: p.id,
    captured_at: p.captured_at,
    download_url: p.download_url,
  }));
  return {
    id: obra.id,
    codigo: obra.codigo,
    nome: obra.nome,
    status: obra.status,
    data_inicio: obra.data_inicio,
    data_prevista_fim: obra.data_prevista_fim,
    construtora: PORTAL_CONSTRUTORA,
    documentos: docs,
    fotos,
  };
}

/** Orçamento vigente que o cliente vê. Promove o de demonstração (rascunho com
 * itens) para `aguardando_aprovacao` na primeira visita, para o fluxo de
 * aprovação ter o que aprovar. */
function resolveOrcamento(obraId: string) {
  const daObra = orcamentos.filter((o) => o.obra_id === obraId && !o.deleted);
  let orc = daObra.find((o) => COMPARTILHAVEL.has(o.status));
  if (!orc) {
    // O de maior preço = o de demonstração (com EAP); os vazios ficam em 0.
    const comValor = daObra
      .map((o) => ({ o, preco: precoDe(o.id) }))
      .sort((a, b) => Number(b.preco) - Number(a.preco))[0];
    if (comValor && Number(comValor.preco) > 0) {
      orc = comValor.o;
      if (orc.status === "rascunho" || orc.status === "em_revisao") {
        updateStatus(orc.id, "aguardando_aprovacao");
      }
    }
  }
  return orc ?? null;
}

function precoDe(orcamentoId: string): string {
  const orc = orcamentos.find((o) => o.id === orcamentoId);
  const versao = versoes.find(
    (v) => v.orcamento_id === orcamentoId && v.numero === orc?.versao_atual,
  );
  return versao?.preco_venda ?? "0";
}

function toPortalOrcamento(orcId: string): PortalOrcamento {
  const orc = orcamentos.find((o) => o.id === orcId)!;
  const d = decisoes.get(orcId);
  return {
    id: orc.id,
    titulo: orc.titulo,
    status: orc.status,
    preco_venda: precoDe(orcId),
    pdf_url: `/_mock/pdf/${orc.id}`,
    decisao: d?.decisao ?? null,
    decidido_em: d?.decidido_em ?? null,
  };
}

export function getPortalOrcamentoMock(token: string): PortalOrcamento {
  const obra = resolveObra(token);
  const orc = resolveOrcamento(obra.id);
  if (!orc) throw new PortalMockError(404, "nenhum orçamento disponível para o cliente");
  return toPortalOrcamento(orc.id);
}

export function decidirOrcamentoMock(
  token: string,
  decisao: "aprovado" | "rejeitado",
): PortalOrcamento {
  const obra = resolveObra(token);
  const orc = resolveOrcamento(obra.id);
  if (!orc) throw new PortalMockError(404, "nenhum orçamento disponível para o cliente");
  if (orc.status !== "aguardando_aprovacao") {
    throw new PortalMockError(409, "orçamento não está aguardando aprovação");
  }
  updateStatus(orc.id, decisao);
  decisoes.set(orc.id, { decisao, decidido_em: new Date().toISOString() });
  return toPortalOrcamento(orc.id);
}

export function getPortalTicketsMock(token: string): PortalTicket[] {
  const obra = resolveObra(token);
  return tickets
    .filter((t) => t.obra_id === obra.id)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .map((t) => ({
      id: t.id,
      titulo: t.titulo,
      status: t.status,
      created_at: t.created_at,
      mensagens: mensagens
        .filter((m) => m.ticket_id === t.id)
        .sort((a, b) => a.created_at.localeCompare(b.created_at)),
    }));
}

export function addPortalMensagemMock(
  ticketId: string,
  body: MensagemCreateInput,
): TicketMensagem {
  const ticket = tickets.find((t) => t.id === ticketId);
  if (!ticket) throw new PortalMockError(404, "chamado não encontrado");
  if (ticket.status === "fechado") throw new PortalMockError(409, "chamado fechado");
  const msg: TicketMensagem = {
    id: nextId(),
    ticket_id: ticketId,
    author_id: null, // cliente (sem user_id no portal)
    content: body.content,
    attachment_paths: body.attachment_paths ?? [],
    created_at: new Date().toISOString(),
  };
  mensagens.push(msg);
  return msg;
}
