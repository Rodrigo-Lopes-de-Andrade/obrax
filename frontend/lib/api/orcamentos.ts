import { api, ApiError } from "./client";
import type {
  EapTree,
  ImportErro,
  ItemCreateInput,
  ItemUpdateInput,
  Orcamento,
  OrcamentoCreateInput,
  OrcamentoDetail,
  OrcamentoStatus,
  Page,
  PrecificacaoInput,
  ProblemDetail,
  ReorderItemInput,
} from "./types";

export interface ListOrcamentosParams {
  obra_id?: string;
  cursor?: string | null;
  limit?: number;
}

function qs(params: Record<string, string | number | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function listOrcamentos(params: ListOrcamentosParams = {}): Promise<Page<Orcamento>> {
  return api.get(`/api/v1/orcamentos${qs({ ...params })}`);
}

export function getOrcamento(id: string): Promise<OrcamentoDetail> {
  return api.get(`/api/v1/orcamentos/${id}`);
}

export function createOrcamento(
  obraId: string,
  input: OrcamentoCreateInput,
): Promise<OrcamentoDetail> {
  return api.post(`/api/v1/obras/${obraId}/orcamentos`, input);
}

export function updateOrcamentoStatus(
  id: string,
  status: OrcamentoStatus,
): Promise<OrcamentoDetail> {
  return api.patch(`/api/v1/orcamentos/${id}/status`, { status });
}

export function deleteOrcamento(id: string): Promise<void> {
  return api.delete(`/api/v1/orcamentos/${id}`);
}

/* ---- Itens da EAP (toda mutação devolve a árvore recalculada) ---- */
export function getEapTree(versaoId: string): Promise<EapTree> {
  return api.get(`/api/v1/orcamentos/versoes/${versaoId}/itens`);
}

export function bulkCreateItens(
  versaoId: string,
  itens: ItemCreateInput[],
): Promise<EapTree> {
  return api.post(`/api/v1/orcamentos/versoes/${versaoId}/itens/bulk`, { itens });
}

export function updateItem(itemId: string, patch: ItemUpdateInput): Promise<EapTree> {
  return api.patch(`/api/v1/orcamentos/itens/${itemId}`, patch);
}

export function deleteItemTree(itemId: string): Promise<EapTree> {
  return api.delete<EapTree>(`/api/v1/orcamentos/itens/${itemId}`);
}

export function duplicateItem(itemId: string): Promise<EapTree> {
  return api.post(`/api/v1/orcamentos/itens/${itemId}/duplicar`, {});
}

export function reorderItens(
  versaoId: string,
  itens: ReorderItemInput[],
): Promise<EapTree> {
  return api.put(`/api/v1/orcamentos/versoes/${versaoId}/itens/ordem`, { itens });
}

export function setPrecificacao(
  versaoId: string,
  input: PrecificacaoInput,
): Promise<EapTree> {
  return api.put(`/api/v1/orcamentos/versoes/${versaoId}/precificacao`, input);
}

/** URL do template XLSX para download direto (F5.5). */
export const TEMPLATE_URL = "/api/v1/orcamentos/importar/modelo";

/** Import multipart — devolve a árvore criada ou lança com os erros por linha. */
export async function importPlanilha(versaoId: string, file: File): Promise<EapTree> {
  const form = new FormData();
  form.append("arquivo", file);
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/orcamentos/versoes/${versaoId}/importar-planilha`,
    { method: "POST", body: form, credentials: "include" },
  );
  const isJson = res.headers.get("content-type")?.includes("json") ?? false;
  const body: unknown = isJson ? await res.json() : undefined;
  if (!res.ok) {
    throw new ApiError(res.status, (body as ProblemDetail) ?? { status: res.status });
  }
  return body as EapTree;
}

/** Extrai os erros linha-a-linha de um ApiError de importação (detail.erros). */
export function importErros(error: unknown): ImportErro[] {
  if (error instanceof ApiError) {
    const detail = error.problem.detail as unknown;
    if (detail && typeof detail === "object" && "erros" in detail) {
      return (detail as { erros: ImportErro[] }).erros;
    }
  }
  return [];
}
