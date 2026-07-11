/**
 * Mock do Módulo 3 (Agentes IA, US-22/23/24) para o MSW. Sem LLM real: as
 * respostas do assistente são determinísticas por palavra-chave (intent
 * routing simplificado), espelhando o comportamento do orquestrador do backend
 * (intake → intent → subagente → responder). As interações auditáveis e as
 * permissões vivem em stores em memória, semeadas sobre as obras do db.ts.
 */
import type {
  AgentChatMessage,
  AgentInteraction,
  AiPermission,
  AiPermissionCreateInput,
  CopilotSuggestInput,
  CopilotSuggestion,
  IaInsights,
} from "@/lib/api/types";

import { ensureSeed, nextId, obras } from "./db";

export class IaMockError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export const aiPermissions: AiPermission[] = [];
export const agentInteractions: AgentInteraction[] = [];
export const chatThread: AgentChatMessage[] = [];

let seeded = false;

function isoAgo(hours: number): string {
  return new Date(Date.now() - hours * 3_600_000).toISOString();
}

export function ensureIaSeed(): void {
  if (seeded) return;
  ensureSeed();
  seeded = true;

  aiPermissions.push(
    {
      id: nextId(),
      whatsapp_number: "+5511988887777",
      role: "consultor",
      daily_limit_cents: 0,
      monthly_limit_cents: 0,
      created_at: isoAgo(240),
    },
    {
      id: nextId(),
      whatsapp_number: "+5511977776666",
      role: "solicitador",
      daily_limit_cents: 50_000,
      monthly_limit_cents: 500_000,
      created_at: isoAgo(120),
    },
  );

  const o0 = obras[0];
  const o1 = obras[1] ?? obras[0];
  agentInteractions.push(
    {
      id: nextId(),
      whatsapp_number: "+5511988887777",
      command: "Qual o status da obra Vila Aurora?",
      intent: "consulta_status",
      agent: "orcamento",
      action: null,
      result: `Obra ${o0?.codigo ?? "OBR-1001"} está em execução, 62% concluída.`,
      status: "ok",
      cost_cents: 4,
      obra_id: o0?.id ?? null,
      obra_codigo: o0?.codigo ?? null,
      reverted_at: null,
      created_at: isoAgo(3),
    },
    {
      id: nextId(),
      whatsapp_number: "+5511977776666",
      command: "Solicitar 20 sacos de cimento para a obra do galpão",
      intent: "criar_compra",
      agent: "compras",
      action: "criar_solicitacao_compra",
      result: "Solicitação de compra #SC-204 criada (20un cimento CP-II).",
      status: "ok",
      cost_cents: 11,
      obra_id: o1?.id ?? null,
      obra_codigo: o1?.codigo ?? null,
      reverted_at: null,
      created_at: isoAgo(20),
    },
    {
      id: nextId(),
      whatsapp_number: "+5511988887777",
      command: "Quanto custou o orçamento aprovado?",
      intent: "consulta_orcamento",
      agent: "orcamento",
      action: null,
      result: "O orçamento aprovado soma R$ 184.500,00 (preço de venda).",
      status: "ok",
      cost_cents: 5,
      obra_id: o0?.id ?? null,
      obra_codigo: o0?.codigo ?? null,
      reverted_at: null,
      created_at: isoAgo(48),
    },
  );
}

/* ---- Feature flags ---- */
export function getFeatureFlagsMock(): Record<string, boolean> {
  return { "ia-module-enabled": true };
}

/* ---- Assistente (F10.1) — mock LLM determinístico ---- */
function respostaAssistente(pergunta: string): string {
  const q = pergunta.toLowerCase();
  const obra = obras[0];
  const codigo = obra?.codigo ?? "OBR-1001";
  const nome = obra?.nome ?? "a obra";
  if (/(status|andamento|progresso|prazo)/.test(q)) {
    return `A obra ${codigo} (${nome}) está em execução, com ~62% concluído e entrega prevista dentro do prazo. Quer o detalhamento por etapa?`;
  }
  if (/(orçament|orcament|custo|valor|preço|preco)/.test(q)) {
    return `O orçamento vigente de ${codigo} soma R$ 184.500,00 de preço de venda (custo direto R$ 142.700,00, BDI 29,3%). Posso abrir a curva ABC dos insumos.`;
  }
  if (/(compra|comprar|solicit|material|insumo)/.test(q)) {
    return `Para registrar uma compra eu preciso do item, quantidade e obra. Ex.: "20 sacos de cimento CP-II para ${codigo}". A ação exige permissão de solicitador (US-23).`;
  }
  if (/(oi|olá|ola|bom dia|boa tarde|ajuda|pode)/.test(q)) {
    return "Olá! Sou o assistente da Obrax. Posso consultar status de obras, resumos de orçamento e registrar solicitações de compra. Como posso ajudar?";
  }
  return `Entendi: "${pergunta}". Posso ajudar com status de obra, resumo de orçamento e solicitações de compra — sobre qual desses você quer seguir?`;
}

export function getAssistenteThreadMock(): AgentChatMessage[] {
  return chatThread;
}

export function enviarAssistenteMensagemMock(content: string): AgentChatMessage {
  const texto = content.trim();
  if (!texto) throw new IaMockError(422, "mensagem vazia");
  chatThread.push({
    id: nextId(),
    role: "user",
    content: texto,
    created_at: new Date().toISOString(),
  });
  const assistant: AgentChatMessage = {
    id: nextId(),
    role: "assistant",
    content: respostaAssistente(texto),
    created_at: new Date().toISOString(),
  };
  chatThread.push(assistant);
  return assistant;
}

/* ---- Auditoria (F10.2) ---- */
export function listarInteracoesMock(params: {
  obraId: string | null;
  agent: string | null;
  cursor: string | null;
  limit: number;
}): { items: AgentInteraction[]; next_cursor: string | null } {
  ensureIaSeed();
  let rows = [...agentInteractions].sort((a, b) => (a.id < b.id ? 1 : -1));
  if (params.obraId) rows = rows.filter((r) => r.obra_id === params.obraId);
  if (params.agent) rows = rows.filter((r) => r.agent === params.agent);
  const after = params.cursor ? rows.filter((r) => r.id < params.cursor!) : rows;
  const items = after.slice(0, params.limit);
  const hasMore = after.length > params.limit;
  return { items, next_cursor: hasMore ? items[items.length - 1].id : null };
}

export function reverterInteracaoMock(id: string): AgentInteraction {
  const it = agentInteractions.find((i) => i.id === id);
  if (!it) throw new IaMockError(404, "interação não encontrada");
  if (!it.action) throw new IaMockError(409, "interação sem ação reversível (consulta)");
  if (it.reverted_at) throw new IaMockError(409, "ação já revertida");
  it.reverted_at = new Date().toISOString();
  it.status = "revertido";
  return it;
}

/* ---- Permissões (F10.3) ---- */
export function listarPermissoesMock(): { items: AiPermission[]; next_cursor: null } {
  ensureIaSeed();
  const items = [...aiPermissions].sort((a, b) => (a.id < b.id ? 1 : -1));
  return { items, next_cursor: null };
}

export function criarPermissaoMock(input: AiPermissionCreateInput): AiPermission {
  const numero = input.whatsapp_number.trim();
  if (!numero) throw new IaMockError(422, "número obrigatório");
  const existente = aiPermissions.find((p) => p.whatsapp_number === numero);
  if (existente) {
    // Upsert: um papel por número por tenant (UNIQUE no backend).
    existente.role = input.role;
    existente.daily_limit_cents = input.daily_limit_cents;
    existente.monthly_limit_cents = input.monthly_limit_cents;
    return existente;
  }
  const nova: AiPermission = {
    id: nextId(),
    whatsapp_number: numero,
    role: input.role,
    daily_limit_cents: input.daily_limit_cents,
    monthly_limit_cents: input.monthly_limit_cents,
    created_at: new Date().toISOString(),
  };
  aiPermissions.push(nova);
  return nova;
}

export function removerPermissaoMock(id: string): void {
  const i = aiPermissions.findIndex((p) => p.id === id);
  if (i === -1) throw new IaMockError(404, "permissão não encontrada");
  aiPermissions.splice(i, 1);
}

/* ---- Copilot (F10.4) ---- */
const COPILOT_BASE: Record<string, CopilotSuggestion[]> = {
  alvenaria: [
    { descricao: "Bloco cerâmico 9x19x39", unidade: "un", quantidade: "1200" },
    { descricao: "Argamassa de assentamento", unidade: "kg", quantidade: "480" },
    { descricao: "Pedreiro (mão de obra)", unidade: "h", quantidade: "64" },
  ],
  piso: [
    { descricao: "Porcelanato 60x60", unidade: "m²", quantidade: "85" },
    { descricao: "Argamassa colante AC-III", unidade: "kg", quantidade: "340" },
    { descricao: "Rejunte flexível", unidade: "kg", quantidade: "25" },
  ],
  pintura: [
    { descricao: "Tinta acrílica premium", unidade: "L", quantidade: "72" },
    { descricao: "Massa corrida PVA", unidade: "kg", quantidade: "120" },
    { descricao: "Pintor (mão de obra)", unidade: "h", quantidade: "48" },
  ],
};

export function copilotSugerirMock(input: CopilotSuggestInput): CopilotSuggestion[] {
  const q = input.descricao.toLowerCase();
  for (const [chave, itens] of Object.entries(COPILOT_BASE)) {
    if (q.includes(chave)) return itens;
  }
  // Fallback genérico derivado da descrição.
  return [
    { descricao: `Material principal — ${input.descricao}`, unidade: "un", quantidade: "100" },
    { descricao: "Mão de obra associada", unidade: "h", quantidade: "40" },
  ];
}

/* ---- Insights (F10.5) ---- */
export function getIaInsightsMock(): IaInsights {
  ensureIaSeed();
  const semana = agentInteractions.filter(
    (i) => Date.parse(i.created_at) > Date.now() - 7 * 24 * 3_600_000,
  );
  const ok = agentInteractions.filter((i) => i.status !== "erro").length;
  const total = agentInteractions.length || 1;
  return {
    acoes_ultima_semana: semana.length,
    economia_tempo_min: 12,
    taxa_sucesso: ok / total,
    ultimas_acoes: [...agentInteractions].sort((a, b) => (a.id < b.id ? 1 : -1)).slice(0, 5),
  };
}
