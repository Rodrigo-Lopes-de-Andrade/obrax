import { api } from "./client";
import type {
  MensagemCreateInput,
  PortalAprovacaoInput,
  PortalLink,
  PortalObra,
  PortalOrcamento,
  PortalTicket,
  TicketMensagem,
} from "./types";

/** Portal do cliente (US-19/US-20). O `token` é a credencial no path — o front
 * o repassa opaco (JWT no backend real; id no mock). Sem header de auth. */

export function getPortalObra(token: string): Promise<PortalObra> {
  return api.get(`/api/v1/portal/obras/${token}`);
}

export function getPortalOrcamento(token: string): Promise<PortalOrcamento> {
  return api.get(`/api/v1/portal/orcamentos/${token}`);
}

export function aprovarOrcamento(
  token: string,
  body: PortalAprovacaoInput,
): Promise<PortalOrcamento> {
  return api.post(`/api/v1/portal/orcamentos/${token}/aprovar`, body);
}

export function rejeitarOrcamento(
  token: string,
  body: PortalAprovacaoInput,
): Promise<PortalOrcamento> {
  return api.post(`/api/v1/portal/orcamentos/${token}/rejeitar`, body);
}

export function getPortalTickets(token: string): Promise<PortalTicket[]> {
  return api.get(`/api/v1/portal/tickets/${token}`);
}

export function addPortalMensagem(
  token: string,
  ticketId: string,
  body: MensagemCreateInput,
): Promise<TicketMensagem> {
  return api.post(`/api/v1/portal/tickets/${token}/${ticketId}/mensagens`, body);
}

/** Admin: emite o link do portal para a obra (owner/admin/gestor). */
export function gerarPortalLink(obraId: string): Promise<PortalLink> {
  return api.post(`/api/v1/obras/${obraId}/portal-link`, {});
}
