"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { DashboardKpis } from "@/components/modules/dashboard/DashboardKpis";
import { IaInsightsCard } from "@/components/modules/ia/IaInsightsCard";
import { ObrasVencidasAlert } from "@/components/modules/dashboard/ObrasVencidasAlert";

export default function DashboardPage() {
  return (
    <>
      {/* F4.1 — Indicadores da empresa (live via GET /dashboard/summary) + alertas. */}
      <div className="mb-4 flex flex-wrap items-end justify-between gap-5">
        <div>
          <h1 className="mb-1 text-[27px] font-extrabold tracking-tight">Indicadores da Empresa</h1>
          <p className="text-sm text-muted-foreground">
            Visão consolidada de obras, chamados e orçamentos
          </p>
        </div>
        <Link
          href="/orcamentos"
          className="flex items-center gap-2 rounded-lg bg-primary px-4.25 py-2.5 text-[13.5px] font-bold text-primary-foreground shadow-[0_4px_14px_rgba(255,107,107,0.28)] hover:bg-primary-hover"
        >
          <Plus className="h-4.25 w-4.25" />
          Novo Orçamento
        </Link>
      </div>
      <div className="mb-4">
        <DashboardKpis />
      </div>
      <div className="mb-8">
        <ObrasVencidasAlert />
      </div>

      {/* F10.5 — Insights dos Agentes IA (gated pela flag ia-module-enabled). */}
      <div className="mb-8">
        <IaInsightsCard />
      </div>
    </>
  );
}
