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

/* ---- Checklist de campo (US-16) — espelho de gestao/checklist/schemas.py. ---- */
export interface ChecklistItem {
  id: string;
  obra_id: string;
  titulo: string;
  completed: boolean;
  completed_at: string | null;
  sort_order: number;
  created_at: string;
}

export interface ChecklistItemCreateInput {
  titulo: string;
  sort_order?: number;
}

export interface ChecklistItemUpdateInput {
  titulo?: string;
  completed?: boolean;
  sort_order?: number;
}

/* ---- Fotos de campo (US-09/US-17) — espelho de gestao/fotos/schemas.py. ---- */
export type PhotoSyncStatus = "pendente" | "sincronizado";

export interface Photo {
  id: string;
  obra_id: string;
  ocorrencia_id: string | null;
  client_photo_id: string;
  sha256: string;
  size_bytes: number;
  sync_status: PhotoSyncStatus;
  captured_at: string;
  synced_at: string | null;
  created_at: string;
  /** URL de download assinada; `null` enquanto pendente (sem objeto no bucket). */
  download_url: string | null;
}

export interface PhotoSyncInput {
  obra_id: string;
  sha256: string;
  size_bytes: number;
  captured_at: string;
}

/** Resposta do /photos/sync: a URL assinada p/ o PUT direto no storage. */
export interface PhotoSyncResult {
  photo_id: string;
  upload_url: string;
  method: string;
  expires_in: number;
}

/* ---- Ocorrências de campo (US-18) — espelho de gestao/ocorrencias/schemas.py. ---- */
export type OcorrenciaStatus = "aberto" | "resolvido";

export interface Ocorrencia {
  id: string;
  obra_id: string;
  titulo: string;
  descricao: string | null;
  status: OcorrenciaStatus;
  gps_lat: number | null;
  gps_lng: number | null;
  photo_ids: string[];
  created_at: string;
}

export interface OcorrenciaCreateInput {
  titulo: string;
  descricao?: string | null;
  gps_lat?: number | null;
  gps_lng?: number | null;
  photo_ids: string[];
}

/* ---- Relatórios gerenciais (US-10) — espelho de gestao/relatorios/schemas.py.
 * Valores financeiros são Decimal serializado como string. ---- */
export interface ObrasStatusLinha {
  status: ObraStatus;
  count: number;
  valor: string;
}

export interface RelatorioObrasAtivas {
  ativas: number;
  valor_ativas: string;
  total: number;
  por_status: ObrasStatusLinha[];
}

export interface OrcamentosStatusLinha {
  status: OrcamentoStatus;
  count: number;
  preco_venda: string;
}

export interface RelatorioOrcamentos {
  total: number;
  preco_venda_total: string;
  pendentes: number;
  por_status: OrcamentosStatusLinha[];
}

/* ------------------------------------------------------------------ *
 * Módulo 2 — Orçamentos (EAP). Espelho de app/modules/orcamento.
 * Todo valor financeiro é Decimal serializado como string (nunca float).
 * ------------------------------------------------------------------ */
export type OrcamentoStatus =
  | "rascunho"
  | "em_revisao"
  | "aguardando_aprovacao"
  | "aprovado"
  | "rejeitado";

/** Fase, Serviço, Insumo/MO — os 3 níveis da EAP. */
export type ItemTipo = "F" | "S" | "I";

export interface Orcamento {
  id: string;
  obra_id: string;
  titulo: string;
  status: OrcamentoStatus;
  versao_atual: number;
  created_at: string;
}

/** Agregados de uma versão (recalculados pelo BudgetCalculator). */
export interface VersaoOut {
  id: string;
  numero: number;
  is_locked: boolean;
  custo_direto: string;
  markup_global: string;
  taxa_adm: string;
  preco_venda: string;
  margem: string;
  created_at: string;
}

export interface OrcamentoDetail extends Orcamento {
  versao: VersaoOut;
}

export interface OrcamentoCreateInput {
  titulo: string;
}

export interface OrcamentoItem {
  id: string;
  versao_id: string;
  parent_id: string | null;
  tipo: ItemTipo;
  depth: number;
  path: string;
  sort_order: number;
  codigo: string | null;
  descricao: string;
  unidade: string | null;
  quantidade: string;
  preco_unitario: string;
  markup_override: string | null;
  custo_total: string;
  subtotal: string;
}

/** Agregados enxutos da versão devolvidos junto da árvore. */
export interface VersaoResumo {
  id: string;
  is_locked: boolean;
  custo_direto: string;
  markup_global: string;
  taxa_adm: string;
  preco_venda: string;
  margem: string;
}

/** Corpo do GET da árvore e de toda mutação de itens. */
export interface EapTree {
  versao: VersaoResumo;
  itens: OrcamentoItem[];
}

export interface ItemCreateInput {
  tipo: ItemTipo;
  parent_id?: string | null;
  codigo?: string | null;
  descricao: string;
  unidade?: string | null;
  quantidade?: string;
  preco_unitario?: string;
  markup_override?: string | null;
}

export interface ItemUpdateInput {
  codigo?: string | null;
  descricao?: string;
  unidade?: string | null;
  quantidade?: string;
  preco_unitario?: string;
  markup_override?: string | null;
}

export interface ReorderItemInput {
  id: string;
  parent_id: string | null;
  sort_order: number;
}

export interface PrecificacaoInput {
  markup_global: string;
  taxa_adm: string;
}

/* ---- Curva ABC (US-14) — espelho de schemas.py `CurvaAbc`.
 * `pct`/`pct_acumulado` são frações (Decimal string, ex. "0.8000"). ---- */
export type AbcClasseNome = "A" | "B" | "C";

export interface AbcItem {
  id: string;
  codigo: string | null;
  descricao: string;
  unidade: string | null;
  custo: string;
  pct: string;
  pct_acumulado: string;
  classe: AbcClasseNome;
}

export interface AbcClasse {
  classe: AbcClasseNome;
  count: number;
  custo: string;
  pct: string;
}

export interface CurvaAbc {
  custo_total: string;
  itens: AbcItem[];
  classes: AbcClasse[];
}

/* ---- PDF do orçamento (US-17) — espelho de schemas.py. ---- */
export interface OrcamentoPdfGerado {
  gerado_em: string;
  content_type: string;
}

export interface OrcamentoPdfStatus extends OrcamentoPdfGerado {
  download_url: string;
}

/** Catálogo de insumos (SINAPI global + custom do tenant). */
export interface Insumo {
  id: string;
  codigo: string;
  descricao: string;
  unidade: string | null;
  categoria: string | null;
  preco_unitario: string;
  is_custom: boolean;
}

/** Erro de validação de importação XLSX, linha-a-linha. */
export interface ImportErro {
  linha: number;
  campo: string;
  mensagem: string;
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
