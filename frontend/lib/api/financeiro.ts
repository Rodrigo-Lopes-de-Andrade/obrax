import { api, downloadBlob } from "./client";
import type {
  AlocacoesPut,
  CategoriaCreate,
  CategoriaOut,
  CategoriaUpdate,
  CronogramaCreate,
  CronogramaGradeOut,
  CurvaSOut,
  DespesaCreate,
  DespesaOut,
  DespesaPagar,
  DespesaPage,
  DespesaParceladaCreate,
  DespesaParceladaOut,
  DespesaStatus,
  DespesaUpdate,
  FluxoCaixaOut,
  MedicaoAprovadaOut,
  MedicaoAprovar,
  MedicaoCreate,
  MedicaoDetail,
  MedicaoItensPut,
  MedicaoPage,
  OrcadoRealizadoOut,
  Periodicidade,
  RecebimentoOut,
  RecebimentoPage,
  RecebimentoReceber,
  RecebimentoStatus,
} from "./types";

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export interface PageParams {
  cursor?: string | null;
  limit?: number;
}
export interface ListDespesasParams extends PageParams {
  status?: DespesaStatus;
  obra_fase_id?: string;
  categoria_id?: string;
  /** Data ISO `YYYY-MM-DD`. */
  de?: string;
  /** Data ISO `YYYY-MM-DD`. */
  ate?: string;
}
export interface ListRecebimentosParams extends PageParams {
  obra_id?: string;
  status?: RecebimentoStatus;
}
export interface FluxoCaixaParams {
  de: string;
  ate: string;
  obra_id?: string;
  periodicidade?: Periodicidade;
}
export interface ExportCsvParams {
  status?: DespesaStatus;
  obra_fase_id?: string;
  categoria_id?: string;
  de?: string;
  ate?: string;
}

// Cronograma
export function createCronograma(obraId: string, input: CronogramaCreate): Promise<CronogramaGradeOut> {
  return api.post(`/api/v1/obras/${obraId}/cronograma`, input);
}
export function getCronograma(obraId: string): Promise<CronogramaGradeOut> {
  return api.get(`/api/v1/obras/${obraId}/cronograma`);
}
export function putAlocacoes(cronogramaId: string, input: AlocacoesPut): Promise<CronogramaGradeOut> {
  return api.put(`/api/v1/cronograma/${cronogramaId}/alocacoes`, input);
}

// Medições
export function listMedicoes(obraId: string, params: PageParams = {}): Promise<MedicaoPage> {
  return api.get(`/api/v1/obras/${obraId}/medicoes${qs({ ...params })}`);
}
export function createMedicao(obraId: string, input: MedicaoCreate): Promise<MedicaoDetail> {
  return api.post(`/api/v1/obras/${obraId}/medicoes`, input);
}
export function getMedicao(id: string): Promise<MedicaoDetail> {
  return api.get(`/api/v1/medicoes/${id}`);
}
export function putMedicaoItens(id: string, input: MedicaoItensPut): Promise<MedicaoDetail> {
  return api.put(`/api/v1/medicoes/${id}/itens`, input);
}
export function aprovarMedicao(id: string, input: MedicaoAprovar = {}): Promise<MedicaoAprovadaOut> {
  return api.post(`/api/v1/medicoes/${id}/aprovar`, input);
}

// Categorias
export function listCategorias(incluirInativas = false): Promise<CategoriaOut[]> {
  return api.get(`/api/v1/financeiro/categorias${qs({ incluir_inativas: incluirInativas || undefined })}`);
}
export function createCategoria(input: CategoriaCreate): Promise<CategoriaOut> {
  return api.post(`/api/v1/financeiro/categorias`, input);
}
export function updateCategoria(id: string, input: CategoriaUpdate): Promise<CategoriaOut> {
  return api.patch(`/api/v1/financeiro/categorias/${id}`, input);
}

// Despesas
export function listDespesas(obraId: string, params: ListDespesasParams = {}): Promise<DespesaPage> {
  return api.get(`/api/v1/obras/${obraId}/despesas${qs({ ...params })}`);
}
export function createDespesa(obraId: string, input: DespesaCreate): Promise<DespesaOut> {
  return api.post(`/api/v1/obras/${obraId}/despesas`, input);
}
export function createDespesaParcelada(
  obraId: string,
  input: DespesaParceladaCreate,
): Promise<DespesaParceladaOut> {
  return api.post(`/api/v1/obras/${obraId}/despesas/parcelada`, input);
}
export function getDespesa(id: string): Promise<DespesaOut> {
  return api.get(`/api/v1/financeiro/despesas/${id}`);
}
export function updateDespesa(id: string, input: DespesaUpdate): Promise<DespesaOut> {
  return api.patch(`/api/v1/financeiro/despesas/${id}`, input);
}
/** DELETE = cancelar (E-10): devolve a despesa com status `cancelada`. */
export function cancelarDespesa(id: string): Promise<DespesaOut> {
  return api.delete(`/api/v1/financeiro/despesas/${id}`);
}
export function pagarDespesa(id: string, input: DespesaPagar): Promise<DespesaOut> {
  return api.post(`/api/v1/financeiro/despesas/${id}/pagar`, input);
}
export function estornarDespesa(id: string): Promise<DespesaOut> {
  return api.post(`/api/v1/financeiro/despesas/${id}/estornar`, {});
}

// Recebimentos
export function listRecebimentos(params: ListRecebimentosParams = {}): Promise<RecebimentoPage> {
  return api.get(`/api/v1/financeiro/recebimentos${qs({ ...params })}`);
}
export function receberRecebimento(id: string, input: RecebimentoReceber): Promise<RecebimentoOut> {
  return api.post(`/api/v1/financeiro/recebimentos/${id}/receber`, input);
}

// Análise
export function getOrcadoRealizado(obraId: string): Promise<OrcadoRealizadoOut> {
  return api.get(`/api/v1/obras/${obraId}/financeiro/orcado-realizado`);
}
export function getCurvaS(obraId: string): Promise<CurvaSOut> {
  return api.get(`/api/v1/obras/${obraId}/financeiro/curva-s`);
}
export function getFluxoCaixa(params: FluxoCaixaParams): Promise<FluxoCaixaOut> {
  return api.get(`/api/v1/financeiro/fluxo-caixa${qs({ ...params })}`);
}
/** CSV de despesas (CA-F14.1) — `text/csv`, baixado com o token. */
export function exportDespesasCsv(obraId: string, params: ExportCsvParams = {}): Promise<Blob> {
  return downloadBlob(`/api/v1/obras/${obraId}/financeiro/export.csv${qs({ ...params })}`);
}
