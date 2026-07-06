"use client";

import { ExternalLink } from "lucide-react";
import { CurvaAbcList } from "@/components/modules/orcamento/CurvaAbcList";
import type { ItemAbc } from "@/lib/types/orcamento";
import { useUiStore } from "@/state/ui";

interface CurvaAbcCardProps {
  itens: ItemAbc[];
}

export function CurvaAbcCard({ itens }: CurvaAbcCardProps) {
  const openBudgetModal = useUiStore((s) => s.openBudgetModal);

  return (
    <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="mb-0.75 text-base font-bold">Curva ABC de Insumos</h3>
          <p className="text-[13px] text-muted-foreground">
            Concentração de custo por insumo · classe A representa 55% do total
          </p>
        </div>
        <button
          type="button"
          onClick={openBudgetModal}
          className="flex items-center gap-1.75 rounded-lg border border-white/8 bg-muted px-3.5 py-2 text-[13px] font-semibold text-subtle-foreground hover:bg-white/10"
        >
          <ExternalLink className="h-3.75 w-3.75" />
          Abrir orçamento
        </button>
      </div>
      <CurvaAbcList itens={itens} showHeader />
    </div>
  );
}
