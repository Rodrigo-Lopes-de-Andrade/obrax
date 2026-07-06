"use client";

import { useUiStore } from "@/state/ui";
import { custoDiretoBase, vendasPorEtapa } from "@/lib/mock/dashboard-obra";
import { formatMoneyRounded, formatPercent, multiply } from "@/lib/decimal";
import Decimal from "decimal.js";

export function VendasTab() {
  const markupPct = useUiStore((s) => s.markupPct);
  const setMarkupPct = useUiStore((s) => s.setMarkupPct);
  const admPct = useUiStore((s) => s.admPct);
  const setAdmPct = useUiStore((s) => s.setAdmPct);

  const cd = new Decimal(custoDiretoBase);
  const markup = multiply(cd, markupPct).div(100);
  const adm = multiply(cd, admPct).div(100);
  const precoVenda = cd.plus(markup).plus(adm);
  const margemEfetiva = precoVenda.gt(0) ? precoVenda.minus(cd).div(precoVenda).mul(100) : new Decimal(0);

  const maiorVenda = Math.max(...vendasPorEtapa.map((v) => v.venda));

  return (
    <div>
      <div className="mb-4 rounded-[10px] border border-white/5 bg-card px-5 py-4.5">
        <div className="mb-4.5 grid grid-cols-2 gap-x-8 gap-y-4.5">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[13px] font-semibold text-subtle-foreground">Markup global</span>
              <span className="font-mono text-sm font-bold text-secondary">{markupPct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={60}
              value={markupPct}
              onChange={(e) => setMarkupPct(Number(e.target.value))}
              className="w-full accent-secondary"
            />
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[13px] font-semibold text-subtle-foreground">Taxa de administração</span>
              <span className="font-mono text-sm font-bold text-secondary">{admPct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={25}
              value={admPct}
              onChange={(e) => setAdmPct(Number(e.target.value))}
              className="w-full accent-secondary"
            />
          </div>
        </div>

        <div className="flex flex-col gap-2.25 border-t border-white/6 pt-3.5">
          <Row label="Custo direto total" value={formatMoneyRounded(cd)} />
          <Row label={`+ Markup global (${markupPct}%)`} value={`+ ${formatMoneyRounded(markup)}`} accent />
          <Row label={`+ Taxa de adm. (${admPct}%)`} value={`+ ${formatMoneyRounded(adm)}`} accent />
          <div className="mt-0.75 flex items-baseline justify-between border-t border-dashed border-white/10 pt-2.75">
            <span className="text-sm font-bold">Preço de venda</span>
            <span className="font-mono text-[19px] font-extrabold text-success">{formatMoneyRounded(precoVenda)}</span>
          </div>
          <Row label="Margem efetiva" value={formatPercent(margemEfetiva)} success />
        </div>
      </div>

      <div className="mb-2.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
        Margem por etapa
      </div>
      <div className="flex flex-col gap-2.75">
        {vendasPorEtapa.map((venda) => (
          <div
            key={venda.etapa}
            className="flex items-center gap-4 rounded-[9px] border border-white/5 bg-card px-4 py-3.5"
          >
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold">{venda.etapa}</div>
              <div className="text-xs text-muted-foreground">
                Custo {formatMoneyRounded(venda.custo)} · Venda {formatMoneyRounded(venda.venda)}
              </div>
            </div>
            <div className="relative h-2 w-40 overflow-hidden rounded-full bg-white/6">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-success"
                style={{ width: `${(venda.venda / maiorVenda) * 100}%` }}
              />
            </div>
            <div className="w-19.5 text-right font-mono text-sm font-extrabold text-success">
              {venda.margemPct}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Row({ label, value, accent, success }: { label: string; value: string; accent?: boolean; success?: boolean }) {
  return (
    <div className="flex justify-between text-[13.5px]">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={`font-mono font-semibold ${success ? "font-bold text-success" : accent ? "text-secondary" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}
