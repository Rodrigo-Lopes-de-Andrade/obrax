"use client";

import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Layers,
  Plus,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { CopilotSuggestion, ItemCreateInput, OrcamentoItem } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  useBulkCreateItens,
  useDeleteItem,
  useDuplicateItem,
  useUpdateItem,
} from "@/lib/hooks/use-orcamentos";
import { buildTree, TIPO_META, type TreeNode } from "./eap-utils";
import { InlineEdit } from "./InlineEdit";
import { InsumoPicker } from "./InsumoPicker";

/** Remove zeros à direita para exibir/editar quantidade e preço. */
function cleanNum(s: string): string {
  if (!s.includes(".")) return s;
  return s.replace(/0+$/, "").replace(/\.$/, "") || "0";
}

const DEFAULT_DESC: Record<string, string> = {
  F: "Nova fase",
  S: "Novo serviço",
  I: "Novo insumo",
};

interface EstruturaTabProps {
  versaoId: string;
  itens: OrcamentoItem[];
  locked: boolean;
  /** F5.5 — abre o diálogo de importação (injetado pelo builder). */
  onImport?: () => void;
}

export function EstruturaTab({ versaoId, itens, locked, onImport }: EstruturaTabProps) {
  const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());
  // Serviço-alvo do seletor de insumos (F5.6); null = fechado.
  const [pickerParent, setPickerParent] = React.useState<string | null>(null);
  const bulk = useBulkCreateItens(versaoId);
  const update = useUpdateItem(versaoId);
  const remove = useDeleteItem(versaoId);
  const duplicate = useDuplicateItem(versaoId);

  const tree = React.useMemo(() => buildTree(itens), [itens]);

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const addChild = (parentId: string | null, tipo: ItemCreateInput["tipo"]) => {
    // Adicionar insumo abre o autocomplete do catálogo (F5.6).
    if (tipo === "I") {
      setPickerParent(parentId);
      return;
    }
    bulk.mutate([{ tipo, parent_id: parentId, descricao: DEFAULT_DESC[tipo] }]);
  };

  const addInsumoBlank = () => {
    if (!pickerParent) return;
    bulk.mutate([
      {
        tipo: "I",
        parent_id: pickerParent,
        descricao: DEFAULT_DESC.I,
        quantidade: "1",
        preco_unitario: "0",
        unidade: "un",
      },
    ]);
    setPickerParent(null);
  };

  const addInsumoFromCatalog = (insumo: {
    codigo: string;
    descricao: string;
    unidade: string | null;
    preco_unitario: string;
  }) => {
    if (!pickerParent) return;
    bulk.mutate([
      {
        tipo: "I",
        parent_id: pickerParent,
        codigo: insumo.codigo,
        descricao: insumo.descricao,
        unidade: insumo.unidade,
        quantidade: "1",
        preco_unitario: insumo.preco_unitario,
      },
    ]);
    setPickerParent(null);
  };

  // F10.4 — insere no serviço-alvo os insumos sugeridos pela IA (preço a definir).
  const addInsumosFromCopilot = (itens: CopilotSuggestion[]) => {
    if (!pickerParent || itens.length === 0) return;
    bulk.mutate(
      itens.map((s) => ({
        tipo: "I" as const,
        parent_id: pickerParent,
        descricao: s.descricao,
        unidade: s.unidade,
        quantidade: s.quantidade,
        preco_unitario: "0",
      })),
    );
    setPickerParent(null);
  };

  const patch = (id: string, field: string, value: string) =>
    update.mutate({ id, patch: { [field]: value } });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-1 pb-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Layers className="size-4" />
          Estrutura Analítica (Fase › Serviço › Insumo)
        </div>
        <div className="flex items-center gap-2">
          {onImport ? (
            <Button variant="outline" size="sm" onClick={onImport} disabled={locked}>
              Importar planilha
            </Button>
          ) : null}
          <Button size="sm" onClick={() => addChild(null, "F")} disabled={locked}>
            <Plus />
            Adicionar fase
          </Button>
        </div>
      </div>

      {/* Cabeçalho das colunas */}
      <div className="grid grid-cols-[1fr_4rem_6rem_8rem_9rem_5rem] items-center gap-2 border-b border-border px-2 py-2 text-[11px] font-semibold tracking-wide text-muted-foreground/70 uppercase">
        <span>Descrição</span>
        <span className="text-right">Un.</span>
        <span className="text-right">Qtd.</span>
        <span className="text-right">Preço unit.</span>
        <span className="text-right">Subtotal</span>
        <span className="text-right">Ações</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {tree.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <Layers className="size-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              Nenhum item ainda. Adicione uma fase{onImport ? " ou importe uma planilha" : ""}.
            </p>
            {!locked && (
              <Button size="sm" variant="outline" onClick={() => addChild(null, "F")}>
                <Plus />
                Adicionar fase
              </Button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {tree.map((node) => (
              <ItemRow
                key={node.id}
                node={node}
                depth={0}
                collapsed={collapsed}
                locked={locked}
                onToggle={toggle}
                onAddChild={addChild}
                onPatch={patch}
                onDelete={(id) => remove.mutate(id)}
                onDuplicate={(id) => duplicate.mutate(id)}
                cleanNum={cleanNum}
              />
            ))}
          </div>
        )}
      </div>

      <InsumoPicker
        open={pickerParent !== null}
        onOpenChange={(o) => !o && setPickerParent(null)}
        onPick={addInsumoFromCatalog}
        onAddBlank={addInsumoBlank}
        onInsertMany={addInsumosFromCopilot}
      />
    </div>
  );
}

interface ItemRowProps {
  node: TreeNode;
  depth: number;
  collapsed: Set<string>;
  locked: boolean;
  onToggle: (id: string) => void;
  onAddChild: (parentId: string, tipo: ItemCreateInput["tipo"]) => void;
  onPatch: (id: string, field: string, value: string) => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
  cleanNum: (s: string) => string;
}

function ItemRow(props: ItemRowProps) {
  const { node, depth, collapsed, locked, onToggle, onAddChild, onPatch, onDelete, onDuplicate, cleanNum } =
    props;
  const meta = TIPO_META[node.tipo];
  const isOpen = !collapsed.has(node.id);
  const isInsumo = node.tipo === "I";

  return (
    <>
      <div
        className={cn(
          "group grid grid-cols-[1fr_4rem_6rem_8rem_9rem_5rem] items-center gap-2 px-2 py-1.5 text-sm hover:bg-white/[0.03]",
          node.tipo === "F" && "bg-primary/[0.04] font-medium",
          node.tipo === "S" && "bg-sky-500/[0.03]",
        )}
      >
        {/* Descrição + indent + toggle */}
        <div className="flex min-w-0 items-center gap-1.5" style={{ paddingLeft: depth * 20 }}>
          {node.tipo !== "I" ? (
            <button
              type="button"
              onClick={() => onToggle(node.id)}
              className="flex size-5 flex-shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
              aria-label={isOpen ? "Recolher" : "Expandir"}
            >
              {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            </button>
          ) : (
            <span className="w-5 flex-shrink-0" />
          )}
          <span className={cn("size-1.5 flex-shrink-0 rounded-full", meta.dot)} />
          {node.codigo ? (
            <span className="flex-shrink-0 rounded bg-muted px-1 py-0.5 text-[10px] font-medium text-muted-foreground tabular-nums">
              {node.codigo}
            </span>
          ) : null}
          <div className="min-w-0 flex-1">
            <InlineEdit
              value={node.descricao}
              disabled={locked}
              onCommit={(v) => v && onPatch(node.id, "descricao", v)}
              className={meta.text}
            />
          </div>
        </div>

        {/* Un. / Qtd / Preço — só folhas (insumo) */}
        <div className="text-right text-muted-foreground">
          {isInsumo ? (
            <InlineEdit value={node.unidade ?? ""} disabled={locked} placeholder="un" onCommit={(v) => onPatch(node.id, "unidade", v)} />
          ) : null}
        </div>
        <div className="text-right tabular-nums">
          {isInsumo ? (
            <InlineEdit value={cleanNum(node.quantidade)} numeric disabled={locked} onCommit={(v) => onPatch(node.id, "quantidade", v || "0")} />
          ) : null}
        </div>
        <div className="text-right tabular-nums">
          {isInsumo ? (
            <InlineEdit value={cleanNum(node.preco_unitario)} numeric disabled={locked} onCommit={(v) => onPatch(node.id, "preco_unitario", v || "0")} />
          ) : null}
        </div>

        {/* Subtotal (agregado) */}
        <div className={cn("text-right tabular-nums", node.tipo === "F" ? "font-semibold" : "text-muted-foreground")}>
          {formatMoney(node.subtotal)}
        </div>

        {/* Ações */}
        <div className="flex items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100">
          {!locked && meta.filho ? (
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-muted-foreground hover:text-primary"
              title={`Adicionar ${meta.filhoLabel}`}
              onClick={() => onAddChild(node.id, meta.filho!)}
            >
              <Plus />
            </Button>
          ) : null}
          {!locked ? (
            <>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground hover:text-foreground"
                title="Duplicar"
                onClick={() => onDuplicate(node.id)}
              >
                <Copy />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground hover:text-destructive"
                title="Excluir"
                onClick={() => onDelete(node.id)}
              >
                <Trash2 />
              </Button>
            </>
          ) : null}
        </div>
      </div>

      {isOpen &&
        node.children.map((child) => (
          <ItemRow key={child.id} {...props} node={child} depth={depth + 1} />
        ))}
    </>
  );
}
