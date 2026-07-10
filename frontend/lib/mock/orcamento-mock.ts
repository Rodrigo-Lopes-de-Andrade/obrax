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
  AbcClasse,
  AbcClasseNome,
  AbcItem,
  CurvaAbc,
  EapTree,
  Insumo,
  ItemCreateInput,
  ItemTipo,
  ItemUpdateInput,
  Orcamento,
  OrcamentoDetail,
  OrcamentoItem,
  OrcamentoPdfGerado,
  OrcamentoPdfStatus,
  OrcamentoStatus,
  ReorderItemInput,
  VersaoOut,
} from "@/lib/api/types";
import { clientes, nextId, obras, usuarios } from "./db";

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

/* ------------------------------ curva ABC -------------------------------- */
// Espelha app/modules/orcamento/services/curva_abc.py: classifica as folhas
// (insumos) por custo direto acumulado (80/15/5). Proibido float — Decimal.js.
const LIMIAR_A = new Decimal("0.80");
const LIMIAR_B = new Decimal("0.95");

function pctFrac(parte: Decimal, total: Decimal): string {
  if (total.lte(0)) return "0.0000";
  return parte.div(total).toDecimalPlaces(4).toFixed(4);
}

function versaoAtualDe(orcamentoId: string): MockVersao {
  const orc = orcamentos.find((o) => o.id === orcamentoId && !o.deleted);
  if (!orc) throw new MockError(404, "orçamento não encontrado");
  const versao = versoes.find(
    (v) => v.orcamento_id === orc.id && v.numero === orc.versao_atual,
  );
  if (!versao) throw new MockError(404, "versão não encontrada");
  return versao;
}

export function curvaAbcOf(orcamentoId: string): CurvaAbc {
  const versao = versaoAtualDe(orcamentoId);
  const its = itens.filter((i) => i.versao_id === versao.id);
  const comFilho = new Set(its.map((i) => i.parent_id).filter((p): p is string => !!p));
  const leaves = its
    .filter((i) => !comFilho.has(i.id))
    .map((i) => ({
      id: i.id,
      codigo: i.codigo,
      descricao: i.descricao,
      unidade: i.unidade,
      custo: new Decimal(i.quantidade).times(i.preco_unitario).toDecimalPlaces(2),
    }));
  // Versão sem itens → curva vazia (mesmo shape do endpoint quando nunca recalc).
  if (leaves.length === 0) return { custo_total: "0", itens: [], classes: [] };

  const total = leaves.reduce((a, l) => a.plus(l.custo), new Decimal(0));
  const ordenados = [...leaves].sort((a, b) => {
    const d = b.custo.comparedTo(a.custo);
    return d !== 0 ? d : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });

  const itensOut: AbcItem[] = [];
  let acumulado = new Decimal(0);
  for (const leaf of ordenados) {
    const antes = acumulado; // acumulado ANTES de incluir este item
    acumulado = acumulado.plus(leaf.custo);
    let classe: AbcClasseNome;
    if (total.lte(0)) classe = "C";
    else if (antes.lt(LIMIAR_A.times(total))) classe = "A";
    else if (antes.lt(LIMIAR_B.times(total))) classe = "B";
    else classe = "C";
    itensOut.push({
      id: leaf.id,
      codigo: leaf.codigo,
      descricao: leaf.descricao,
      unidade: leaf.unidade,
      custo: leaf.custo.toFixed(2),
      pct: pctFrac(leaf.custo, total),
      pct_acumulado: pctFrac(acumulado, total),
      classe,
    });
  }

  const classes: AbcClasse[] = (["A", "B", "C"] as const).map((nome) => {
    const grupo = itensOut.filter((it) => it.classe === nome);
    const custoClasse = grupo.reduce((a, it) => a.plus(it.custo), new Decimal(0));
    return {
      classe: nome,
      count: grupo.length,
      custo: custoClasse.toFixed(2),
      pct: pctFrac(custoClasse, total),
    };
  });

  return { custo_total: total.toFixed(2), itens: itensOut, classes };
}

/* -------------------------------- PDF ------------------------------------ */
// Espelha o job síncrono do backend (B6.3): gerar grava um artefato e um
// timestamp; o "download" no mock é uma página HTML servida em /_mock/pdf/:id.
const pdfs = new Map<string, { gerado_em: string }>();

export function gerarPdfMock(orcamentoId: string): OrcamentoPdfGerado {
  versaoAtualDe(orcamentoId); // valida existência (404)
  const gerado_em = new Date().toISOString();
  pdfs.set(orcamentoId, { gerado_em });
  return { gerado_em, content_type: "text/html; charset=utf-8" };
}

export function pdfStatusMock(orcamentoId: string): OrcamentoPdfStatus {
  versaoAtualDe(orcamentoId);
  const pdf = pdfs.get(orcamentoId);
  if (!pdf) throw new MockError(404, "PDF ainda não foi gerado");
  return {
    gerado_em: pdf.gerado_em,
    content_type: "text/html; charset=utf-8",
    download_url: `/_mock/pdf/${orcamentoId}`,
  };
}

const EMPRESA_NOME = "Sua Construtora Ltda";
const STATUS_LABEL: Record<OrcamentoStatus, string> = {
  rascunho: "Rascunho",
  em_revisao: "Em revisão",
  aguardando_aprovacao: "Aguardando aprovação",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};

const esc = (s: string | null | undefined) =>
  (s ?? "").replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!,
  );
const brl = (v: Decimal.Value) =>
  `R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    new Decimal(v).toNumber(),
  )}`;
const pctBr = (frac: Decimal.Value) =>
  `${new Decimal(frac).times(100).toFixed(2).replace(".", ",")}%`;

/** HTML do "PDF" para o viewer do mock (espelha o template do backend, B6.4). */
export function renderPdfHtmlMock(orcamentoId: string): string {
  const orc = orcamentos.find((o) => o.id === orcamentoId && !o.deleted);
  if (!orc) return "<!DOCTYPE html><title>404</title><p>Orçamento não encontrado.</p>";
  const versao = versaoAtualDe(orcamentoId);
  const obra = obras.find((o) => o.id === orc.obra_id);
  const cliente = clientes.find((c) => c.id === obra?.cliente_id);
  const its = treeOf(versao.id).itens;
  const curva = curvaAbcOf(orcamentoId);
  const iniciais =
    EMPRESA_NOME.split(" ")
      .slice(0, 2)
      .map((p) => p[0])
      .join("")
      .toUpperCase() || "?";

  const linhas = its
    .map((i) => {
      const cls = i.tipo === "F" ? "row-f" : i.tipo === "S" ? "row-s" : "row-i";
      const folha = i.tipo === "I";
      const cod = i.codigo ? `<span class="cod">${esc(i.codigo)}</span> ` : "";
      return `<tr class="${cls}"><td style="padding-left:${8 + i.depth * 16}px">${cod}${esc(i.descricao)}</td>
        <td class="c">${folha ? esc(i.unidade) : ""}</td>
        <td class="n">${folha ? new Decimal(i.quantidade).toFixed(2).replace(".", ",") : ""}</td>
        <td class="n">${folha ? brl(i.preco_unitario) : ""}</td>
        <td class="n">${brl(i.subtotal)}</td></tr>`;
    })
    .join("");

  const abc =
    curva.itens.length === 0
      ? '<p class="empty">Sem itens classificados.</p>'
      : `<table><thead><tr><th>Classe</th><th class="n">Itens</th><th class="n">Custo</th><th class="n">% custo</th></tr></thead><tbody>${curva.classes
          .map(
            (c) =>
              `<tr><td><span class="dot dot-${c.classe}"></span>Classe ${c.classe}</td><td class="n">${c.count}</td><td class="n">${brl(c.custo)}</td><td class="n">${pctBr(c.pct)}</td></tr>`,
          )
          .join("")}</tbody></table>`;

  return `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>${esc(orc.titulo)} — ${esc(obra?.codigo)}</title>
<style>
@page{size:A4;margin:18mm 16mm}*{box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1e293b;font-size:11px;line-height:1.45;margin:24px;background:#fff}
.head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #4f46e5;padding-bottom:12px;margin-bottom:16px}
.brand{display:flex;align-items:center;gap:12px}.logo{width:52px;height:52px;border-radius:8px;background:#4f46e5;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px}
.bname{font-size:15px;font-weight:700}.meta{text-align:right}.title{font-size:20px;font-weight:700;color:#4f46e5}.sub{font-weight:600}
.tag{display:inline-block;background:#eef2ff;color:#4338ca;border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;margin-left:4px}
.date{color:#64748b;font-size:10px}.parties{display:flex;gap:16px;margin-bottom:18px}
.party{flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px}
.plabel{text-transform:uppercase;font-size:9px;letter-spacing:.6px;color:#64748b}.pname{font-weight:600;font-size:12px}.pdoc{color:#64748b}
h2{font-size:12px;font-weight:700;color:#334155;margin:18px 0 8px;text-transform:uppercase;letter-spacing:.4px}
table{width:100%;border-collapse:collapse}th{text-align:left;background:#f1f5f9;color:#475569;font-size:9px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid #cbd5e1}
td{padding:5px 8px;border-bottom:1px solid #eef2f7}.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.c{text-align:center;color:#64748b}
.row-f td{background:#eef2ff;font-weight:700}.row-s td{background:#f8fafc;font-weight:600}
.cod{display:inline-block;background:#e2e8f0;color:#475569;border-radius:3px;padding:0 4px;font-size:9px}
.grid{display:flex;gap:16px;margin-top:18px}.grid>div{flex:1}
.kv td{padding:4px 2px}.kv .total td{border-top:2px solid #4f46e5;font-weight:700;font-size:13px;color:#4f46e5}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}.dot-A{background:#dc2626}.dot-B{background:#d97706}.dot-C{background:#059669}
.empty{color:#94a3b8;padding:12px}
</style></head><body>
<div class="head"><div class="brand"><div class="logo">${esc(iniciais)}</div><div class="bname">${esc(EMPRESA_NOME)}</div></div>
<div class="meta"><div class="title">Orçamento</div><div class="sub">${esc(orc.titulo)}</div>
<div><span class="tag">Rev. ${orc.versao_atual}</span><span class="tag">${esc(STATUS_LABEL[orc.status])}</span></div>
<div class="date">Emitido em ${new Date().toLocaleDateString("pt-BR")}</div></div></div>
<div class="parties"><div class="party"><div class="plabel">Cliente</div><div class="pname">${esc(cliente?.nome)}</div><div class="pdoc">${esc(cliente?.documento)}</div></div>
<div class="party"><div class="plabel">Obra</div><div class="pname">${esc(obra?.nome)}</div><div class="pdoc">${esc(obra?.codigo)}</div></div></div>
<h2>Estrutura Analítica do Projeto</h2>
<table><thead><tr><th>Descrição</th><th>Un.</th><th class="n">Qtd.</th><th class="n">Preço unit.</th><th class="n">Subtotal</th></tr></thead>
<tbody>${linhas || '<tr><td colspan="5" class="empty">Sem itens.</td></tr>'}</tbody></table>
<div class="grid"><div><h2>Resumo</h2><table class="kv">
<tr><td>Custo direto</td><td class="n">${brl(versao.custo_direto)}</td></tr>
<tr><td>Markup global</td><td class="n">${pctBr(versao.markup_global)}</td></tr>
<tr><td>Taxa de administração</td><td class="n">${pctBr(versao.taxa_adm)}</td></tr>
<tr><td>Margem</td><td class="n">${pctBr(versao.margem)}</td></tr>
<tr class="total"><td>Preço de venda</td><td class="n">${brl(versao.preco_venda)}</td></tr></table></div>
<div><h2>Curva ABC</h2>${abc}</div></div>
</body></html>`;
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
