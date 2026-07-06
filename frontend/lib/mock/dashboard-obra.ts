import type {
  Fase,
  ItemAbc,
  VendaEtapa,
  CronogramaGrupo,
  Versao,
  CompareRow,
  ContaPagarReceber,
} from "@/lib/types/orcamento";

export const obraAtual = {
  nome: "Residencial Vila Aurora",
  unidades: 32,
  etapaAtual: "Alvenaria · Torre B",
  equipeCanteiro: 48,
  entregaPrevista: "Dez/2026",
  diasAtraso: 18,
  avancoFisicoPct: 64,
  avancoPrevistoPct: 71,
};

export const kpis = {
  custoRealizado: 4_820_000,
  custoPrevisto: 5_100_000,
  receitaContratada: 7_400_000,
  aditivos: 320_000,
  margemBrutaPct: 34.8,
  margemVarPp: 1.2,
  avancoFisicoPct: 64,
  desvioAvancoPp: 7,
};

/** % acumulado por mês (Jan..Dez) */
export const curvaSPrevisto = [4, 11, 21, 34, 48, 62, 74, 84, 91, 96, 99, 100];
export const curvaSRealizado = [3, 9, 18, 29, 41, 52, 60, 64];
export const curvaSMeses = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];
export const curvaSBaseMilhoes = 5.1;

/** Saldo líquido diário em milhares de reais, últimos 15 dias úteis */
export const fluxoCaixaDiario = [42, -18, 30, 12, -55, 8, 60, -22, 15, 38, -12, 50, 28, -40, 66];
export const fluxoEntradasMi = 1.24;
export const fluxoSaidasMi = 0.98;

export const contasPagarReceber: ContaPagarReceber[] = [
  { id: "c1", titulo: "Medição 07 — Aurora Inc.", vencimento: "Recebe 05/07", valor: 480_000, tipo: "receber" },
  { id: "c2", titulo: "Concreteira Premix", vencimento: "Vence 02/07", valor: 128_400, tipo: "pagar" },
  { id: "c3", titulo: "Folha — equipe estrutura", vencimento: "Vence 05/07", valor: 96_200, tipo: "pagar" },
  { id: "c4", titulo: "Aço Gerdau — pedido #4412", vencimento: "Vence 08/07", valor: 73_500, tipo: "pagar" },
  { id: "c5", titulo: "Aditivo elétrica", vencimento: "Recebe 12/07", valor: 64_000, tipo: "receber" },
];
export const aReceber7d = 544_000;
export const aPagar7d = 298_000;

export const curvaAbc: ItemAbc[] = [
  { classe: "A", nome: "Concreto usinado FCK 30", pct: 22, pctAcumulado: 100, valor: 1_060_000 },
  { classe: "A", nome: "Armação aço CA-50", pct: 18, pctAcumulado: 82, valor: 868_000 },
  { classe: "A", nome: "Mão de obra estrutura", pct: 15, pctAcumulado: 68, valor: 723_000 },
  { classe: "B", nome: "Forma de compensado", pct: 9, pctAcumulado: 41, valor: 434_000 },
  { classe: "B", nome: "Laje pré-moldada", pct: 7, pctAcumulado: 32, valor: 337_000 },
  { classe: "C", nome: "Revestimento cerâmico", pct: 4, pctAcumulado: 18, valor: 193_000 },
];

export const vendasPorEtapa: VendaEtapa[] = [
  { etapa: "Fundação", custo: 920_000, venda: 1_280_000, margemPct: 28 },
  { etapa: "Estrutura", custo: 2_150_000, venda: 3_100_000, margemPct: 31 },
  { etapa: "Alvenaria / Vedação", custo: 1_180_000, venda: 1_740_000, margemPct: 32 },
  { etapa: "Acabamento", custo: 1_420_000, venda: 2_380_000, margemPct: 40 },
];

export const cronogramaMeses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago"];
export const cronograma: CronogramaGrupo[] = [
  { etapa: "Fundação", startPct: 0, widthPct: 18, color: "var(--color-success)" },
  { etapa: "Estrutura", startPct: 12, widthPct: 40, color: "var(--color-secondary)" },
  { etapa: "Alvenaria", startPct: 40, widthPct: 30, color: "var(--chart-4)" },
  { etapa: "Instalações", startPct: 55, widthPct: 28, color: "var(--chart-4)" },
  { etapa: "Acabamento", startPct: 72, widthPct: 28, color: "var(--color-primary)" },
];

export const versoes: Versao[] = [
  { rev: "Rev 3", atual: true, canCompare: false, data: "04/Jun/2026", autor: "Marina Alves", valorTotal: 7_400_000, bdiPct: 24.5, itens: 142, dot: "var(--color-success)" },
  { rev: "Rev 2", atual: false, canCompare: true, data: "18/Mai/2026", autor: "Carlos Motta", valorTotal: 7_120_000, bdiPct: 23, itens: 138, dot: "var(--muted-foreground)" },
  { rev: "Rev 1", atual: false, canCompare: true, data: "02/Mai/2026", autor: "Carlos Motta", valorTotal: 6_890_000, bdiPct: 22, itens: 130, dot: "var(--muted-foreground)" },
];

export const compareRows: CompareRow[] = [
  { item: "Concreto FCK 30 usinado", r2: "R$ 1.020.000", r3: "R$ 1.096.700", diff: "+R$ 76.700", tipo: "up" },
  { item: "Aço CA-50", r2: "R$ 798.000", r3: "R$ 868.200", diff: "+R$ 70.200", tipo: "up" },
  { item: "Escoramento metálico", r2: "R$ 168.000", r3: "R$ 118.400", diff: "−R$ 49.600", tipo: "down" },
  { item: "Laje pré-moldada", r2: "—", r3: "R$ 337.000", diff: "+R$ 337.000", tipo: "up" },
  { item: "BDI aplicado", r2: "23,0%", r3: "24,5%", diff: "+1,5 p.p.", tipo: "up" },
];

export const orcamentoInfo = {
  numero: "ORC-2026-0042",
  titulo: "Estrutura — Torre B",
  cliente: "Aurora Incorporações SA",
  obra: "Residencial Vila Aurora",
  responsavelTecnico: "Marina Alves · CREA 12345-D",
  regime: "Empreitada global",
  dataBase: "04/2026 · SINAPI",
  bdiPct: 24.5,
};

export const custoDiretoBase = 5_820_000;

export const eapInicial: Fase[] = [
  {
    id: "f1",
    nome: "FASE 1 — Fundação",
    open: true,
    servicos: [
      {
        id: "f1s1",
        nome: "Escavação mecânica",
        open: true,
        insumos: [
          { id: "f1s1i1", codigo: "05.001", desc: "Escavação c/ retroescavadeira", unid: "m³", qtd: 30, preco: 400 },
          { id: "f1s1i2", codigo: "05.002", desc: "Operador de máquina", unid: "h", qtd: 8, preco: 135 },
        ],
      },
      {
        id: "f1s2",
        nome: "Concretagem",
        open: true,
        insumos: [
          { id: "f1s2i1", codigo: "05.010", desc: "Concreto magro FCK 15", unid: "m³", qtd: 12, preco: 380 },
          { id: "f1s2i2", codigo: "05.011", desc: "Sapata armada FCK 30", unid: "m³", qtd: 48, preco: 620 },
          { id: "f1s2i3", codigo: "05.012", desc: "Servente", unid: "h", qtd: 120, preco: 28 },
        ],
      },
    ],
  },
  {
    id: "f2",
    nome: "FASE 2 — Estrutura",
    open: false,
    servicos: [
      {
        id: "f2s1",
        nome: "Pilares e vigas",
        open: true,
        insumos: [
          { id: "f2s1i1", codigo: "07.001", desc: "Concreto FCK 30 usinado", unid: "m³", qtd: 220, preco: 498.5 },
          { id: "f2s1i2", codigo: "07.002", desc: "Aço CA-50 corte e dobra", unid: "kg", qtd: 18500, preco: 9.85 },
          { id: "f2s1i3", codigo: "07.003", desc: "Forma compensado 18mm", unid: "m²", qtd: 1240, preco: 62.4 },
        ],
      },
      {
        id: "f2s2",
        nome: "Lajes",
        open: true,
        insumos: [
          { id: "f2s2i1", codigo: "07.010", desc: "Laje pré-moldada treliçada", unid: "m²", qtd: 980, preco: 118 },
          { id: "f2s2i2", codigo: "07.011", desc: "Carpinteiro", unid: "h", qtd: 480, preco: 38 },
        ],
      },
    ],
  },
  {
    id: "f3",
    nome: "FASE 3 — Alvenaria",
    open: false,
    servicos: [
      {
        id: "f3s1",
        nome: "Vedação",
        open: true,
        insumos: [
          { id: "f3s1i1", codigo: "09.001", desc: "Bloco cerâmico 14x19x39", unid: "un", qtd: 12500, preco: 1.85 },
          { id: "f3s1i2", codigo: "09.002", desc: "Argamassa de assentamento", unid: "m³", qtd: 64, preco: 290 },
          { id: "f3s1i3", codigo: "09.003", desc: "Pedreiro", unid: "h", qtd: 620, preco: 34 },
        ],
      },
    ],
  },
];

export const impErrRows = [
  { linha: "47", campo: "Preço unit.", problema: 'Valor inválido: "R$abc"' },
  { linha: "89", campo: "Fase", problema: "Fase vazia — obrigatório" },
  { linha: "201", campo: "Unidade", problema: '"M2" → use "m²"' },
];
