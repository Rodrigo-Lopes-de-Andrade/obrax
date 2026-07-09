/**
 * Mock do Módulo 2 (Orçamentos) para o MSW. Espelha o backend:
 * BudgetCalculator (recalc cascata bottom-up em Decimal.js), materialized path,
 * máquina de status e validação de hierarquia F→S→I. Auto-contido (só depende
 * de `db.ts` para obras/usuários/nextId) para evitar ciclos de import.
 *
 * A importação XLSX é simulada: o parser real vive no backend (B5.5). Aqui o
 * mock demonstra os estados da UI — erros por linha quando o nome do arquivo
 * contém "erro", sucesso (hierarquia canônica) caso contrário.
 */
import Decimal from "decimal.js";

import type {
  EapTree,
  Insumo,
  ItemCreateInput,
  ItemTipo,
  ItemUpdateInput,
  Orcamento,
  OrcamentoDetail,
  OrcamentoItem,
  OrcamentoStatus,
  ReorderItemInput,
  VersaoOut,
} from "@/lib/api/types";
import { nextId, obras, usuarios } from "./db";

Decimal.set({ rounding: Decimal.ROUND_HALF_UP });

export type MockOrcamento = Orcamento & { deleted: boolean; created_by: string | null };
export type MockVersao = VersaoOut & { orcamento_id: string };

export const orcamentos: MockOrcamento[] = [];
export const versoes: MockVersao[] = [];
export const itens: OrcamentoItem[] = [];
export const insumos: Insumo[] = [];

const money = (d: Decimal, dp = 2) => d.toFixed(dp);

/* ---------------------------- motor de cálculo --------------------------- */
export function recalcVersao(versaoId: string): void {
  const versao = versoes.find((v) => v.id === versaoId);
  if (!versao) return;
  const items = itens.filter((i) => i.versao_id === versaoId);
  const byId = new Map(items.map((i) => [i.id, i]));
  const children = new Map<string | null, OrcamentoItem[]>();
  for (const it of items) {
    const arr = children.get(it.parent_id) ?? [];
    arr.push(it);
    children.set(it.parent_id, arr);
  }

  const globalMarkup = new Decimal(versao.markup_global);
  const taxaAdm = new Decimal(versao.taxa_adm);
  let custoDireto = new Decimal(0);

  const effMarkup = (node: OrcamentoItem): Decimal => {
    let cur: OrcamentoItem | undefined = node;
    while (cur) {
      if (cur.markup_override != null) return new Decimal(cur.markup_override);
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
    return globalMarkup;
  };

  const walk = (node: OrcamentoItem): Decimal => {
    const kids = children.get(node.id) ?? [];
    const custo = new Decimal(node.quantidade).times(node.preco_unitario);
    node.custo_total = money(custo);
    let sub: Decimal;
    if (kids.length) {
      sub = kids.reduce((a, k) => a.plus(walk(k)), new Decimal(0));
    } else {
      custoDireto = custoDireto.plus(custo.toDecimalPlaces(2));
      sub = custo.times(new Decimal(1).plus(effMarkup(node))).toDecimalPlaces(2);
    }
    node.subtotal = money(sub);
    return sub;
  };

  const roots = children.get(null) ?? [];
  const total = roots.reduce((a, r) => a.plus(walk(r)), new Decimal(0));
  const precoVenda = total.times(new Decimal(1).plus(taxaAdm)).toDecimalPlaces(2);
  const margem = precoVenda.gt(0)
    ? precoVenda.minus(custoDireto).div(precoVenda).toDecimalPlaces(4)
    : new Decimal(0);
  versao.custo_direto = money(custoDireto);
  versao.preco_venda = money(precoVenda);
  versao.margem = money(margem, 4);
}

export function reindexPaths(versaoId: string): void {
  const items = itens.filter((i) => i.versao_id === versaoId);
  const byId = new Map(items.map((i) => [i.id, i]));
  const children = new Map<string | null, OrcamentoItem[]>();
  for (const it of items) {
    const arr = children.get(it.parent_id) ?? [];
    arr.push(it);
    children.set(it.parent_id, arr);
  }
  const walk = (id: string, parentPath: string, depth: number): void => {
    const it = byId.get(id);
    if (!it) return;
    it.path = parentPath ? `${parentPath}.${id}` : id;
    it.depth = depth;
    for (const c of children.get(id) ?? []) walk(c.id, it.path, depth + 1);
  };
  for (const r of children.get(null) ?? []) walk(r.id, "", 0);
}

/* --------------------------------- erros --------------------------------- */
export class MockError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string | Record<string, unknown>,
  ) {
    super(typeof detail === "string" ? detail : "erro");
  }
}

const PARENT_TIPO: Record<ItemTipo, ItemTipo | null> = { F: null, S: "F", I: "S" };

const TRANSICOES: Record<OrcamentoStatus, OrcamentoStatus[]> = {
  rascunho: ["em_revisao", "aguardando_aprovacao"],
  em_revisao: ["rascunho", "aguardando_aprovacao"],
  aguardando_aprovacao: ["aprovado", "rejeitado", "em_revisao"],
  rejeitado: ["rascunho", "em_revisao"],
  aprovado: [],
};

function versaoEditavel(versaoId: string): MockVersao {
  const versao = versoes.find((v) => v.id === versaoId);
  if (!versao) throw new MockError(404, "versão não encontrada");
  if (versao.is_locked) throw new MockError(409, "versão aprovada é imutável");
  return versao;
}

/* ------------------------------- consultas ------------------------------- */
function versaoResumo(v: MockVersao) {
  return {
    id: v.id,
    is_locked: v.is_locked,
    custo_direto: v.custo_direto,
    markup_global: v.markup_global,
    taxa_adm: v.taxa_adm,
    preco_venda: v.preco_venda,
    margem: v.margem,
  };
}

export function treeOf(versaoId: string): EapTree {
  const versao = versoes.find((v) => v.id === versaoId);
  if (!versao) throw new MockError(404, "versão não encontrada");
  const its = itens
    .filter((i) => i.versao_id === versaoId)
    .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  return { versao: versaoResumo(versao), itens: its.map((i) => ({ ...i })) };
}

export function detailOf(orcamentoId: string): OrcamentoDetail {
  const orc = orcamentos.find((o) => o.id === orcamentoId && !o.deleted);
  if (!orc) throw new MockError(404, "orçamento não encontrado");
  const versao = versoes.find(
    (v) => v.orcamento_id === orc.id && v.numero === orc.versao_atual,
  );
  if (!versao) throw new MockError(404, "versão não encontrada");
  const { orcamento_id: _drop, ...vout } = versao;
  void _drop;
  return {
    id: orc.id,
    obra_id: orc.obra_id,
    titulo: orc.titulo,
    status: orc.status,
    versao_atual: orc.versao_atual,
    created_at: orc.created_at,
    versao: vout,
  };
}

/* ------------------------------- mutações -------------------------------- */
export function createOrcamento(obraId: string, titulo: string): OrcamentoDetail {
  const orcId = nextId();
  orcamentos.push({
    id: orcId,
    obra_id: obraId,
    titulo,
    status: "rascunho",
    versao_atual: 1,
    created_at: new Date().toISOString(),
    deleted: false,
    created_by: usuarios[0]?.id ?? null,
  });
  versoes.push({
    id: nextId(),
    orcamento_id: orcId,
    numero: 1,
    is_locked: false,
    custo_direto: "0.00",
    markup_global: "0.0000",
    taxa_adm: "0.0000",
    preco_venda: "0.00",
    margem: "0.0000",
    created_at: new Date().toISOString(),
  });
  return detailOf(orcId);
}

export function updateStatus(orcamentoId: string, status: OrcamentoStatus): OrcamentoDetail {
  const orc = orcamentos.find((o) => o.id === orcamentoId && !o.deleted);
  if (!orc) throw new MockError(404, "orçamento não encontrado");
  if (status !== orc.status && !TRANSICOES[orc.status].includes(status)) {
    throw new MockError(409, `transição inválida: ${orc.status} → ${status}`);
  }
  orc.status = status;
  if (status === "aprovado") {
    const versao = versoes.find(
      (v) => v.orcamento_id === orc.id && v.numero === orc.versao_atual,
    );
    if (versao) versao.is_locked = true;
  }
  return detailOf(orcamentoId);
}

export function softDeleteOrcamento(orcamentoId: string): void {
  const orc = orcamentos.find((o) => o.id === orcamentoId && !o.deleted);
  if (!orc) throw new MockError(404, "orçamento não encontrado");
  orc.deleted = true;
}

function novoItem(
  versaoId: string,
  input: ItemCreateInput,
  parent: string | null,
  sortOrder: number,
): OrcamentoItem {
  return {
    id: nextId(),
    versao_id: versaoId,
    parent_id: parent,
    tipo: input.tipo,
    depth: 0,
    path: "",
    sort_order: sortOrder,
    codigo: input.codigo ?? null,
    descricao: input.descricao,
    unidade: input.unidade ?? null,
    quantidade: input.quantidade ?? "0",
    preco_unitario: input.preco_unitario ?? "0",
    markup_override: input.markup_override ?? null,
    custo_total: "0.00",
    subtotal: "0.00",
  };
}

function nextOrdem(versaoId: string, parent: string | null): number {
  const irmaos = itens.filter((i) => i.versao_id === versaoId && i.parent_id === parent);
  return irmaos.reduce((max, i) => Math.max(max, i.sort_order), -1) + 1;
}

export function bulkCreate(versaoId: string, novos: ItemCreateInput[]): EapTree {
  versaoEditavel(versaoId);
  const tipos = new Map(
    itens.filter((i) => i.versao_id === versaoId).map((i) => [i.id, i.tipo]),
  );
  const ordem = new Map<string | null, number>();
  for (const input of novos) {
    const esperado = PARENT_TIPO[input.tipo];
    const parent = input.parent_id ?? null;
    if (esperado === null) {
      if (parent !== null) throw new MockError(422, `hierarquia inválida (${input.tipo})`);
    } else if (parent === null || tipos.get(parent) !== esperado) {
      throw new MockError(422, `hierarquia inválida (${input.tipo} exige pai ${esperado})`);
    }
    const base = ordem.get(parent) ?? nextOrdem(versaoId, parent);
    ordem.set(parent, base + 1);
    const item = novoItem(versaoId, input, parent, base);
    itens.push(item);
    tipos.set(item.id, item.tipo);
  }
  reindexPaths(versaoId);
  recalcVersao(versaoId);
  return treeOf(versaoId);
}

export function updateItem(itemId: string, patch: ItemUpdateInput): EapTree {
  const item = itens.find((i) => i.id === itemId);
  if (!item) throw new MockError(404, "item não encontrado");
  versaoEditavel(item.versao_id);
  const keys = Object.keys(patch) as (keyof ItemUpdateInput)[];
  if (keys.length === 0) throw new MockError(422, "nada para atualizar");
  for (const k of keys) {
    // @ts-expect-error atribuição dinâmica dos campos permitidos
    item[k] = patch[k] ?? null;
  }
  recalcVersao(item.versao_id);
  return treeOf(item.versao_id);
}

export function deleteItem(itemId: string): EapTree {
  const item = itens.find((i) => i.id === itemId);
  if (!item) throw new MockError(404, "item não encontrado");
  versaoEditavel(item.versao_id);
  // Remove a subárvore (cascata da self-FK).
  const remover = new Set<string>([itemId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const i of itens) {
      if (i.parent_id && remover.has(i.parent_id) && !remover.has(i.id)) {
        remover.add(i.id);
        changed = true;
      }
    }
  }
  for (let i = itens.length - 1; i >= 0; i--) {
    if (remover.has(itens[i].id)) itens.splice(i, 1);
  }
  reindexPaths(item.versao_id);
  recalcVersao(item.versao_id);
  return treeOf(item.versao_id);
}

export function duplicateItem(itemId: string): EapTree {
  const original = itens.find((i) => i.id === itemId);
  if (!original) throw new MockError(404, "item não encontrado");
  versaoEditavel(original.versao_id);
  const versaoId = original.versao_id;
  const children = new Map<string | null, OrcamentoItem[]>();
  for (const it of itens.filter((i) => i.versao_id === versaoId)) {
    const arr = children.get(it.parent_id) ?? [];
    arr.push(it);
    children.set(it.parent_id, arr);
  }
  // Empurra os irmãos seguintes.
  for (const irmao of children.get(original.parent_id) ?? []) {
    if (irmao.sort_order > original.sort_order) irmao.sort_order += 1;
  }
  const clone = (src: OrcamentoItem, parent: string | null, ordem: number): void => {
    const novo: OrcamentoItem = {
      ...src,
      id: nextId(),
      parent_id: parent,
      sort_order: ordem,
      path: "",
      depth: 0,
    };
    itens.push(novo);
    (children.get(src.id) ?? []).forEach((c, idx) => clone(c, novo.id, idx));
  };
  clone(original, original.parent_id, original.sort_order + 1);
  reindexPaths(versaoId);
  recalcVersao(versaoId);
  return treeOf(versaoId);
}

export function reorder(versaoId: string, ordem: ReorderItemInput[]): EapTree {
  versaoEditavel(versaoId);
  const tipos = new Map(
    itens.filter((i) => i.versao_id === versaoId).map((i) => [i.id, i.tipo]),
  );
  for (const mov of ordem) {
    const tipo = tipos.get(mov.id);
    if (!tipo) throw new MockError(404, "item não encontrado");
    const esperado = PARENT_TIPO[tipo];
    if (esperado === null) {
      if (mov.parent_id !== null) throw new MockError(422, "hierarquia inválida");
    } else if (mov.parent_id === null || tipos.get(mov.parent_id) !== esperado) {
      throw new MockError(422, "hierarquia inválida");
    }
  }
  for (const mov of ordem) {
    const item = itens.find((i) => i.id === mov.id);
    if (item) {
      item.parent_id = mov.parent_id;
      item.sort_order = mov.sort_order;
    }
  }
  reindexPaths(versaoId);
  recalcVersao(versaoId);
  return treeOf(versaoId);
}

export function setPrecificacao(
  versaoId: string,
  markupGlobal: string,
  taxaAdm: string,
): EapTree {
  const versao = versaoEditavel(versaoId);
  versao.markup_global = new Decimal(markupGlobal).toFixed(4);
  versao.taxa_adm = new Decimal(taxaAdm).toFixed(4);
  recalcVersao(versaoId);
  return treeOf(versaoId);
}

/** Import simulado (o parser real está no backend). Nome com "erro" → 422. */
export function importPlanilhaMock(versaoId: string, filename: string): EapTree {
  versaoEditavel(versaoId);
  if (/erro|invalid/i.test(filename)) {
    throw new MockError(422, {
      erros: [
        { linha: 2, campo: "tipo", mensagem: "serviço sem fase anterior" },
        { linha: 4, campo: "descricao", mensagem: "descrição obrigatória" },
        { linha: 4, campo: "quantidade", mensagem: "quantidade não é um número" },
        { linha: 7, campo: "tipo", mensagem: "tipo inválido (use F, S ou I)" },
      ],
    });
  }
  const fase: ItemCreateInput = { tipo: "F", descricao: "Estrutura (importada)" };
  bulkCreate(versaoId, [fase]);
  const faseId = itens.filter((i) => i.versao_id === versaoId && i.tipo === "F").at(-1)!.id;
  bulkCreate(versaoId, [
    { tipo: "S", parent_id: faseId, descricao: "Pilares" },
  ]);
  const servId = itens.filter((i) => i.versao_id === versaoId && i.tipo === "S").at(-1)!.id;
  return bulkCreate(versaoId, [
    {
      tipo: "I",
      parent_id: servId,
      codigo: "SINAPI-000123",
      descricao: "Concreto usinado fck 30MPa",
      unidade: "m³",
      quantidade: "32",
      preco_unitario: "520.00",
    },
    {
      tipo: "I",
      parent_id: servId,
      codigo: "SINAPI-000456",
      descricao: "Fôrma de madeira",
      unidade: "m²",
      quantidade: "180",
      preco_unitario: "65.00",
    },
  ]);
}

/* ------------------------------- seed ------------------------------------ */
const CATS: [string, string, string, number][] = [
  ["Movimentação de Terra", "Escavação manual em solo", "m³", 62],
  ["Fundações", "Estaca escavada Ø30cm", "m", 95],
  ["Fundações", "Sapata de concreto armado", "m³", 980],
  ["Concreto e Formas", "Concreto usinado fck 25MPa", "m³", 480],
  ["Concreto e Formas", "Concreto usinado fck 30MPa", "m³", 520],
  ["Concreto e Formas", "Fôrma de madeira compensada", "m²", 65],
  ["Concreto e Formas", "Armadura de aço CA-50", "kg", 12.3],
  ["Alvenaria", "Alvenaria de bloco cerâmico", "m²", 88],
  ["Alvenaria", "Verga e contraverga", "m", 42],
  ["Revestimentos", "Chapisco", "m²", 14],
  ["Revestimentos", "Emboço", "m²", 38],
  ["Revestimentos", "Porcelanato retificado 80x80", "m²", 165],
  ["Cobertura", "Telha cerâmica", "m²", 78],
  ["Cobertura", "Estrutura de madeira p/ telhado", "m²", 110],
  ["Instalações Elétricas", "Ponto de tomada", "un", 95],
  ["Instalações Elétricas", "Ponto de iluminação", "un", 105],
  ["Instalações Elétricas", "Cabo flexível 2,5mm²", "m", 4.2],
  ["Instalações Hidráulicas", "Ponto de água fria", "un", 155],
  ["Instalações Hidráulicas", "Ponto de esgoto", "un", 185],
  ["Instalações Hidráulicas", "Tubo PVC soldável 25mm", "m", 12.5],
  ["Esquadrias", "Porta de madeira semi-oca", "un", 560],
  ["Esquadrias", "Janela de alumínio de correr", "m²", 620],
  ["Pintura", "Massa corrida PVA", "m²", 18],
  ["Pintura", "Pintura látex acrílica", "m²", 32],
  ["Impermeabilização", "Manta asfáltica 4mm", "m²", 92],
  ["Louças e Metais", "Bacia sanitária com caixa acoplada", "un", 720],
  ["Louças e Metais", "Torneira de mesa para lavatório", "un", 240],
];

function seedInsumos(): void {
  const variantes = ["fornecimento e instalação", "somente material", "padrão médio"];
  let n = 0;
  for (let v = 0; v < variantes.length; v++) {
    for (const [categoria, base, unidade, preco] of CATS) {
      n += 1;
      insumos.push({
        id: nextId(),
        codigo: `SINAPI-${String(n).padStart(6, "0")}`,
        descricao: `${base} - ${variantes[v]}`,
        unidade,
        categoria,
        preco_unitario: (preco * (1 + v * 0.06)).toFixed(4),
        is_custom: false,
      });
    }
  }
}

type SeedNode = [ItemCreateInput, SeedNode[]];

function seedOrcamentoDemo(obraId: string, titulo: string): string {
  const detail = createOrcamento(obraId, titulo);
  const versaoId = detail.versao.id;
  const versao = versoes.find((v) => v.id === versaoId)!;
  versao.markup_global = "0.2500";
  versao.taxa_adm = "0.0800";

  const arvore: SeedNode[] = [
    [
      { tipo: "F", descricao: "Serviços Preliminares" },
      [
        [
          { tipo: "S", descricao: "Instalação do canteiro" },
          [
            [{ tipo: "I", codigo: "SINAPI-000015", descricao: "Tapume de madeira", unidade: "m²", quantidade: "80", preco_unitario: "58.00" }, []],
            [{ tipo: "I", codigo: "SINAPI-000016", descricao: "Barracão de obra", unidade: "m²", quantidade: "24", preco_unitario: "320.00" }, []],
          ],
        ],
      ],
    ],
    [
      { tipo: "F", descricao: "Fundações" },
      [
        [
          { tipo: "S", descricao: "Estacas" },
          [[{ tipo: "I", codigo: "SINAPI-000002", descricao: "Estaca escavada Ø30cm", unidade: "m", quantidade: "120", preco_unitario: "95.00" }, []]],
        ],
        [
          { tipo: "S", descricao: "Blocos e vigas baldrame" },
          [
            [{ tipo: "I", codigo: "SINAPI-000004", descricao: "Concreto usinado fck 25MPa", unidade: "m³", quantidade: "18", preco_unitario: "480.00" }, []],
            [{ tipo: "I", codigo: "SINAPI-000007", descricao: "Armadura de aço CA-50", unidade: "kg", quantidade: "850", preco_unitario: "12.30" }, []],
          ],
        ],
      ],
    ],
    [
      { tipo: "F", descricao: "Estrutura" },
      [
        [
          { tipo: "S", descricao: "Pilares, vigas e lajes" },
          [
            [{ tipo: "I", codigo: "SINAPI-000006", descricao: "Fôrma de madeira compensada", unidade: "m²", quantidade: "240", preco_unitario: "65.00" }, []],
            [{ tipo: "I", codigo: "SINAPI-000005", descricao: "Concreto usinado fck 30MPa", unidade: "m³", quantidade: "45", preco_unitario: "520.00", markup_override: "0.3000" }, []],
          ],
        ],
      ],
    ],
  ];

  const inserir = (node: SeedNode, parent: string | null): void => {
    bulkCreate(versaoId, [{ ...node[0], parent_id: parent }]);
    const created = itens
      .filter((i) => i.versao_id === versaoId && i.parent_id === parent)
      .at(-1)!;
    for (const child of node[1]) inserir(child, created.id);
  };
  for (const fase of arvore) inserir(fase, null);
  recalcVersao(versaoId);
  return detail.id;
}

let seeded = false;
export function ensureOrcamentoSeed(): void {
  if (seeded) return;
  seeded = true;
  seedInsumos();
  if (obras.length === 0) return;
  const nova = obras[obras.length - 1];
  seedOrcamentoDemo(nova.id, "Orçamento Executivo — Rev. 1");
  // Um segundo, em rascunho vazio, para exercitar o builder do zero.
  createOrcamento(nova.id, "Orçamento Preliminar");
}
