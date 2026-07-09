"use client";

import * as React from "react";
import { Loader2, PackageSearch, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Insumo } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useInsumos } from "@/lib/hooks/use-insumos";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (insumo: Insumo) => void;
  onAddBlank: () => void;
}

/** ComboBox de insumos com busca servidor-side (debounce 500ms) e navegação
 * por teclado. Escala é resolvida no servidor (cursor pagination) — só o topo
 * dos resultados é renderizado, sem travar com 10k itens. */
export function InsumoPicker({ open, onOpenChange, onPick, onAddBlank }: Props) {
  const [term, setTerm] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [active, setActive] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const id = setTimeout(() => setDebounced(term), 500);
    return () => clearTimeout(id);
  }, [term]);

  React.useEffect(() => {
    if (open) {
      setTerm("");
      setDebounced("");
      setActive(0);
      // foco no próximo tick (após montar)
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const { data, isFetching } = useInsumos({ search: debounced, limit: 40 }, open);
  const items = data?.items ?? [];

  React.useEffect(() => setActive(0), [debounced]);

  if (!open) return null;

  const select = (insumo: Insumo | undefined) => {
    if (insumo) onPick(insumo);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      select(items[active]);
    } else if (e.key === "Escape") {
      onOpenChange(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/50 p-4 pt-[12vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="flex max-h-[70vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-popover shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Search className="size-4 flex-shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Buscar insumo por descrição ou código…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {isFetching ? (
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          ) : null}
        </div>

        <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto py-1">
          {items.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center text-sm text-muted-foreground">
              <PackageSearch className="size-7 opacity-40" />
              {debounced ? "Nenhum insumo encontrado." : "Digite para buscar no catálogo SINAPI."}
            </div>
          ) : (
            items.map((insumo, i) => (
              <button
                key={insumo.id}
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => select(insumo)}
                className={cn(
                  "flex w-full items-center gap-3 px-4 py-2 text-left text-sm",
                  i === active ? "bg-primary/12" : "hover:bg-white/5",
                )}
              >
                <span className="flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground tabular-nums">
                  {insumo.codigo}
                </span>
                <span className="min-w-0 flex-1 truncate">{insumo.descricao}</span>
                {insumo.unidade ? (
                  <span className="flex-shrink-0 text-xs text-muted-foreground">
                    {insumo.unidade}
                  </span>
                ) : null}
                <span className="flex-shrink-0 tabular-nums text-muted-foreground">
                  {formatMoney(insumo.preco_unitario)}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-2.5">
          <span className="text-xs text-muted-foreground">
            ↑↓ navegar · Enter selecionar · Esc fechar
          </span>
          <Button variant="outline" size="sm" onClick={onAddBlank}>
            <Plus />
            Adicionar em branco
          </Button>
        </div>
      </div>
    </div>
  );
}
