"use client";

import { ArrowLeft, GitCompare, Plus } from "lucide-react";
import { useUiStore } from "@/state/ui";
import { versoes, compareRows } from "@/lib/mock/dashboard-obra";
import { formatMoneyMillions, formatPercent } from "@/lib/decimal";

export function VersoesTab() {
  const compareOpen = useUiStore((s) => s.compareOpen);
  const toggleCompare = useUiStore((s) => s.toggleCompare);

  if (compareOpen) {
    return (
      <div>
        <div className="mb-4 flex items-center gap-3">
          <button
            type="button"
            onClick={toggleCompare}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-lg border border-white/7 bg-white/5 text-muted-foreground"
          >
            <ArrowLeft className="h-4.25 w-4.25" />
          </button>
          <h3 className="text-base font-bold">
            Rev 2 <span className="text-[#5b6072]">→</span> Rev 3
          </h3>
        </div>

        <div className="overflow-hidden rounded-[10px] border border-white/6">
          <div className="grid grid-cols-[1.8fr_1fr_1fr_1.1fr] border-b border-white/6 bg-card text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            <div className="px-3.5 py-2.75">Item</div>
            <div className="px-3.5 py-2.75 text-right">Rev 2</div>
            <div className="px-3.5 py-2.75 text-right">Rev 3</div>
            <div className="px-3.5 py-2.75 text-right">Diferença</div>
          </div>
          {compareRows.map((row) => (
            <div
              key={row.item}
              className="grid grid-cols-[1.8fr_1fr_1fr_1.1fr] items-center border-b border-white/4"
              style={{ background: row.tipo === "up" ? "rgba(56,217,169,0.08)" : "rgba(255,107,107,0.08)" }}
            >
              <div className="px-3.5 py-2.75 text-[13px] font-medium">{row.item}</div>
              <div className="px-3.5 py-2.75 text-right font-mono text-[12.5px] text-muted-foreground">{row.r2}</div>
              <div className="px-3.5 py-2.75 text-right font-mono text-[12.5px]">{row.r3}</div>
              <div
                className={`px-3.5 py-2.75 text-right font-mono text-[12.5px] font-bold ${
                  row.tipo === "up" ? "text-success" : "text-primary"
                }`}
              >
                {row.diff}
              </div>
            </div>
          ))}
          <div className="grid grid-cols-[1.8fr_1fr_1fr_1.1fr] items-center bg-card">
            <div className="px-3.5 py-3.25 text-[13px] font-bold tracking-wide text-muted-foreground uppercase">
              Valor total
            </div>
            <div className="px-3.5 py-3.25 text-right font-mono text-[13px] text-muted-foreground">R$ 7,12 mi</div>
            <div className="px-3.5 py-3.25 text-right font-mono text-[13px] font-bold">R$ 7,40 mi</div>
            <div className="px-3.5 py-3.25 text-right font-mono text-[13px] font-extrabold text-success">
              +R$ 280 mil
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-bold">Histórico de revisões</h3>
        <button
          type="button"
          className="flex items-center gap-1.75 rounded-lg border border-white/8 bg-muted px-3.5 py-2 text-[13px] font-semibold text-subtle-foreground"
        >
          <Plus className="h-3.75 w-3.75" />
          Nova revisão
        </button>
      </div>

      <div className="flex flex-col">
        {versoes.map((versao) => (
          <div key={versao.rev} className="flex gap-3.5 border-b border-white/5 py-4">
            <div className="flex flex-col items-center pt-0.75">
              <span
                className="h-2.75 w-2.75 rounded-full border-2 border-popover"
                style={{ background: versao.dot, boxShadow: `0 0 0 2px ${versao.dot}33` }}
              />
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-[14.5px] font-bold">{versao.rev}</span>
                {versao.atual && (
                  <span className="rounded-full bg-success/14 px-2.25 py-0.5 text-xs font-bold text-success">
                    Atual
                  </span>
                )}
                <span className="font-mono text-[12.5px] text-muted-foreground">{versao.data}</span>
                <span className="text-[12.5px] text-muted-foreground">· {versao.autor}</span>
              </div>
              <div className="mt-1.25 font-mono text-[12.5px] text-subtle-foreground">
                {formatMoneyMillions(versao.valorTotal)} · BDI {formatPercent(versao.bdiPct)} · {versao.itens} itens
              </div>
              <div className="mt-2.5 flex gap-2">
                <button className="rounded-md border border-white/12 px-3 py-1.25 text-xs font-semibold text-subtle-foreground">
                  Ver
                </button>
                {versao.atual && (
                  <button className="rounded-md border border-white/12 px-3 py-1.25 text-xs font-semibold text-subtle-foreground">
                    Exportar PDF
                  </button>
                )}
                {versao.canCompare && (
                  <button
                    type="button"
                    onClick={toggleCompare}
                    className="flex items-center gap-1.5 rounded-md border border-secondary/40 px-3 py-1.25 text-xs font-semibold text-secondary"
                  >
                    <GitCompare className="h-3.25 w-3.25" />
                    Comparar com Rev 3
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
