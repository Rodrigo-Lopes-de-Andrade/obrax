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
