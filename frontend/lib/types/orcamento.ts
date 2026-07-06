export interface Insumo {
  id: string;
  codigo: string;
  desc: string;
  unid: string;
  qtd: number;
  preco: number;
}

export interface Servico {
  id: string;
  nome: string;
  open: boolean;
  insumos: Insumo[];
}

export interface Fase {
  id: string;
  nome: string;
  open: boolean;
  servicos: Servico[];
}

export type AbcClasse = "A" | "B" | "C";

export interface ItemAbc {
  classe: AbcClasse;
  nome: string;
  pct: number;
  pctAcumulado: number;
  valor: number;
}

export interface VendaEtapa {
  etapa: string;
  custo: number;
  venda: number;
  margemPct: number;
}

export interface CronogramaGrupo {
  etapa: string;
  startPct: number;
  widthPct: number;
  color: string;
}

export interface Versao {
  rev: string;
  atual: boolean;
  canCompare: boolean;
  data: string;
  autor: string;
  valorTotal: number;
  bdiPct: number;
  itens: number;
  dot: string;
}

export interface CompareRow {
  item: string;
  r2: string;
  r3: string;
  diff: string;
  tipo: "up" | "down";
}

export interface ContaPagarReceber {
  id: string;
  titulo: string;
  vencimento: string;
  valor: number;
  tipo: "receber" | "pagar";
}

export type PdfState = "idle" | "loading" | "done";
export type ImportState = "closed" | "upload" | "processing" | "errors" | "clean" | "done";
export type OrcamentoTab = "Dados" | "Custos" | "Vendas" | "Cronograma" | "Curva ABC" | "Versões";
