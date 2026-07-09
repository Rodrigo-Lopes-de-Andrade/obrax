/**
 * Tipos do contrato REST — espelho dos schemas.py de
 * backend/app/modules/gestao (clientes e obras).
 *
 * INTERINO: enquanto `make gen-types` (openapi-typescript) não está no
 * pipeline, estes tipos são mantidos à mão a partir dos schemas Pydantic. Ao
 * ligar o backend real, substituir por `frontend/lib/api.d.ts` gerado
 * (ver docs/CLAUDE.md > Contrato Front ↔ Back).
 *
 * Convenções: IDs UUID (string), timestamps ISO 8601, `valor_contrato` é
 * Decimal serializado como string (nunca float — precisão financeira).
 */

export type ObraStatus =
  | "planejamento"
  | "execucao"
  | "pausada"
  | "concluida"
  | "cancelada";

export type TipoPessoa = "PF" | "PJ";

export interface Cliente {
  id: string;
  tipo_pessoa: TipoPessoa;
  documento: string;
  nome: string;
  telefone: string | null;
  email: string | null;
  created_at: string;
}

export interface Obra {
  id: string;
  cliente_id: string;
  status: ObraStatus;
  codigo: string;
  nome: string;
  data_inicio: string | null;
  data_prevista_fim: string | null;
  data_real_fim: string | null;
  valor_contrato: string | null;
  created_at: string;
}

export interface ObraCreateInput {
  cliente_id: string;
  codigo: string;
  nome: string;
  status?: ObraStatus;
  data_inicio?: string | null;
  data_prevista_fim?: string | null;
  data_real_fim?: string | null;
  valor_contrato?: string | null;
}

/** PATCH: todos opcionais; `cliente_id` é imutável (não exposto). */
export interface ObraUpdateInput {
  codigo?: string;
  nome?: string;
  status?: ObraStatus;
  data_inicio?: string | null;
  data_prevista_fim?: string | null;
  data_real_fim?: string | null;
  valor_contrato?: string | null;
}

export type DocumentoTipo =
  | "projeto"
  | "contrato"
  | "nota_fiscal"
  | "foto"
  | "outro";

export interface Documento {
  id: string;
  obra_id: string;
  nome: string;
  tipo: DocumentoTipo;
  categoria: string | null;
  visivel_cliente: boolean;
  size_bytes: number | null;
  sha256: string | null;
  /** `true` quando o upload foi confirmado (storage_path preenchido). */
  confirmed: boolean;
  created_at: string;
}

/** Corpo do POST /obras/{id}/documentos (cria o registro pendente). */
export interface DocumentoCreateInput {
  nome: string;
  tipo: DocumentoTipo;
  sha256: string;
  size_bytes: number;
  categoria?: string | null;
}

/** Resposta do create: a URL assinada para o PUT direto no storage. */
export interface DocumentoUpload {
  documento_id: string;
  upload_url: string;
  method: string;
  expires_in: number;
}

/** PATCH /documentos/{id}: categoria e/ou visibilidade. */
export interface DocumentoUpdateInput {
  categoria?: string | null;
  visivel_cliente?: boolean;
}

export interface Membro {
  id: string;
  user_id: string;
  nome: string;
  email: string;
  papel: string;
  created_at: string;
}

export interface MembroCreateInput {
  user_id: string;
  papel: string;
}

/** Usuário do tenant (para o seletor de "adicionar membro"). */
export interface Usuario {
  id: string;
  nome: string;
  email: string;
}

export type TicketStatus = "aberto" | "andamento" | "resolvido" | "fechado";

export interface Ticket {
  id: string;
  obra_id: string;
  titulo: string;
  descricao: string | null;
  status: TicketStatus;
  created_by: string | null;
  created_at: string;
}

export interface TicketCreateInput {
  titulo: string;
  descricao?: string | null;
}

export interface TicketMensagem {
  id: string;
  ticket_id: string;
  author_id: string | null;
  content: string;
  attachment_paths: string[];
  created_at: string;
}

export interface MensagemCreateInput {
  content: string;
  attachment_paths?: string[];
}

/** KPIs agregados do dashboard admin (GET /dashboard/summary, B4.4).
 * `obras_valor_total` é Decimal serializado como string. */
export interface DashboardSummary {
  obras_ativas: number;
  obras_valor_total: string;
  tickets_abertos: number;
  orcamentos_pendentes: number;
}

export interface Page<T> {
  items: T[];
  /** `id` do último item; `null` = fim. */
  next_cursor: string | null;
}

/** RFC 7807 Problem Details — formato de erro da API. */
export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: { loc?: (string | number)[]; msg?: string; type?: string }[];
}
