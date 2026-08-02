"use client";

import { DashboardKpis } from "@/components/modules/dashboard/DashboardKpis";
import { ObrasVencidasAlert } from "@/components/modules/dashboard/ObrasVencidasAlert";
import { ObrasResumoCard } from "@/components/modules/dashboard/ObrasResumoCard";
import { IaInsightsCard } from "@/components/modules/ia/IaInsightsCard";

export default function DashboardPage() {
  return (
    <>
      {/* F4.1 — Indicadores da empresa (live via GET /dashboard/summary) + alertas. */}
      <div className="mb-4">
        <h1 className="mb-1 text-[27px] font-extrabold tracking-tight">Indicadores da Empresa</h1>
        <p className="text-sm text-muted-foreground">
          Visão consolidada de obras, chamados e orçamentos
        </p>
      </div>
      <div className="mb-4">
        <DashboardKpis />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ObrasResumoCard />
        <ObrasVencidasAlert />
      </div>

      {/* F10.5 — Insights dos Agentes IA (gated pela flag ia-module-enabled). */}
      <div className="mb-8">
        <IaInsightsCard />
      </div>
    </>
  );
}
