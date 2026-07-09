import type { ItemTipo, OrcamentoItem } from "@/lib/api/types";

export interface TreeNode extends OrcamentoItem {
  children: TreeNode[];
}

/** Monta a árvore a partir da lista plana, ordenando irmãos por `sort_order`
 * (o backend devolve por `path` — a ordem de exibição é do frontend). */
export function buildTree(itens: OrcamentoItem[]): TreeNode[] {
  const nodes = new Map<string, TreeNode>();
  for (const it of itens) nodes.set(it.id, { ...it, children: [] });
  const roots: TreeNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.parent_id ? nodes.get(node.parent_id) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  const sortRec = (arr: TreeNode[]): void => {
    arr.sort((a, b) => a.sort_order - b.sort_order);
    arr.forEach((n) => sortRec(n.children));
  };
  sortRec(roots);
  return roots;
}

export interface TipoMeta {
  label: string;
  /** Rótulo do filho que este nível adiciona (null p/ folha). */
  filho: ItemTipo | null;
  filhoLabel: string | null;
  dot: string;
  text: string;
}

export const TIPO_META: Record<ItemTipo, TipoMeta> = {
  F: { label: "Fase", filho: "S", filhoLabel: "Serviço", dot: "bg-primary", text: "text-foreground" },
  S: { label: "Serviço", filho: "I", filhoLabel: "Insumo", dot: "bg-sky-400", text: "text-foreground" },
  I: { label: "Insumo", filho: null, filhoLabel: null, dot: "bg-emerald-400", text: "text-muted-foreground" },
};
