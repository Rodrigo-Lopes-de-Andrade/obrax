"use client";

import { FileText, X, FileDown, Loader2, Check } from "lucide-react";
import { useUiStore } from "@/state/ui";
import { orcamentoInfo } from "@/lib/mock/dashboard-obra";
import type { OrcamentoTab } from "@/lib/types/orcamento";
import { DadosTab } from "@/components/modules/orcamento/tabs/DadosTab";
import { CustosTab } from "@/components/modules/orcamento/tabs/CustosTab";
import { VendasTab } from "@/components/modules/orcamento/tabs/VendasTab";
import { CronogramaTab } from "@/components/modules/orcamento/tabs/CronogramaTab";
import { AbcTab } from "@/components/modules/orcamento/tabs/AbcTab";
import { VersoesTab } from "@/components/modules/orcamento/tabs/VersoesTab";

const TABS: OrcamentoTab[] = ["Dados", "Custos", "Vendas", "Cronograma", "Curva ABC", "Versões"];

const PDF_MAP = {
  idle: { label: "Gerar PDF", Icon: FileDown, spin: false, className: "bg-white/5 border-white/10 text-subtle-foreground" },
  loading: { label: "Gerando PDF…", Icon: Loader2, spin: true, className: "bg-white/5 border-white/10 text-muted-foreground" },
  done: { label: "PDF pronto — Baixar", Icon: Check, spin: false, className: "bg-success/14 border-success/40 text-success" },
} as const;

export function BudgetModal() {
  const open = useUiStore((s) => s.budgetModalOpen);
  const closeBudgetModal = useUiStore((s) => s.closeBudgetModal);
  const activeTab = useUiStore((s) => s.activeTab);
  const setActiveTab = useUiStore((s) => s.setActiveTab);
  const pdfState = useUiStore((s) => s.pdfState);
  const generatePdf = useUiStore((s) => s.generatePdf);

  if (!open) return null;

  const pdf = PDF_MAP[pdfState];

  return (
    <div
      onClick={closeBudgetModal}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/66 p-8 backdrop-blur-[2px]"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[88vh] w-full max-w-270 flex-col overflow-hidden rounded-[14px] border border-white/8 bg-popover shadow-[0_30px_80px_rgba(0,0,0,0.55)]"
      >
        <div className="border-b border-white/6 px-6 pt-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="flex h-10.5 w-10.5 items-center justify-center rounded-[10px] bg-secondary/15">
                <FileText className="h-5.25 w-5.25 text-secondary" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-[19px] font-extrabold tracking-tight">{orcamentoInfo.titulo}</h2>
                  <span className="rounded-md bg-white/5 px-2.25 py-0.75 font-mono text-xs text-muted-foreground">
                    {orcamentoInfo.numero}
                  </span>
                </div>
                <p className="mt-0.75 text-[13px] text-muted-foreground">
                  {orcamentoInfo.obra} · base SINAPI {orcamentoInfo.dataBase.split(" · ")[0]} · BDI{" "}
                  {orcamentoInfo.bdiPct.toFixed(1).replace(".", ",")}%
                </p>
              </div>
            </div>
            <div className="flex flex-shrink-0 items-center gap-2.5">
              <button
                type="button"
                onClick={generatePdf}
                className={`flex items-center gap-2 rounded-lg border px-3.5 py-2.25 text-[13px] font-semibold ${pdf.className}`}
              >
                <pdf.Icon className={`h-3.75 w-3.75 ${pdf.spin ? "animate-spin" : ""}`} />
                {pdf.label}
              </button>
              <button
                type="button"
                onClick={closeBudgetModal}
                className="flex h-9 w-9 items-center justify-center rounded-[9px] border border-white/7 bg-white/5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-4.5 flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`border-b-2 px-4 py-2.75 text-sm font-semibold transition-colors ${
                  activeTab === tab ? "border-primary text-foreground" : "border-transparent text-muted-foreground"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "Dados" && <DadosTab />}
          {activeTab === "Custos" && <CustosTab />}
          {activeTab === "Vendas" && <VendasTab />}
          {activeTab === "Cronograma" && <CronogramaTab />}
          {activeTab === "Curva ABC" && <AbcTab />}
          {activeTab === "Versões" && <VersoesTab />}
        </div>

        <div className="flex items-center justify-between border-t border-white/6 bg-[#1b1e27] px-6 py-4">
          <div className="text-[13px] text-muted-foreground">Última edição há 2 min · salvo automaticamente</div>
          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={closeBudgetModal}
              className="rounded-lg border border-white/12 px-4.5 py-2.5 text-[13.5px] font-semibold text-subtle-foreground"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={closeBudgetModal}
              className="rounded-lg bg-primary px-5 py-2.5 text-[13.5px] font-bold text-primary-foreground shadow-[0_4px_14px_rgba(255,107,107,0.28)] hover:bg-primary-hover"
            >
              Salvar orçamento
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
