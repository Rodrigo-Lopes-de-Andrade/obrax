"use client";

import { TrendingDown, FileSignature, Percent, AlertTriangle, Plus } from "lucide-react";
import { KpiCard } from "@/components/shared/KpiCard";
import { CurvaSChart } from "@/components/modules/obra/CurvaSChart";
import { FluxoCaixaChart } from "@/components/modules/obra/FluxoCaixaChart";
import { StatusObraCard } from "@/components/modules/obra/StatusObraCard";
import { ContasList } from "@/components/modules/obra/ContasList";
import { CurvaAbcCard } from "@/components/modules/obra/CurvaAbcCard";
import { BudgetModal } from "@/components/modules/orcamento/BudgetModal";
import { ImportSpreadsheetModal } from "@/components/modules/orcamento/ImportSpreadsheetModal";
import { DashboardKpis } from "@/components/modules/dashboard/DashboardKpis";
import { IaInsightsCard } from "@/components/modules/ia/IaInsightsCard";
import { ObrasVencidasAlert } from "@/components/modules/dashboard/ObrasVencidasAlert";
import { useUiStore } from "@/state/ui";
import { formatMoneyMillionsParts, formatMoneyRounded, formatPercent } from "@/lib/decimal";
import {
  kpis,
  obraAtual,
  curvaSPrevisto,
  curvaSRealizado,
  curvaSMeses,
  curvaSBaseMilhoes,
  fluxoCaixaDiario,
  fluxoEntradasMi,
  fluxoSaidasMi,
  contasPagarReceber,
  aReceber7d,
  aPagar7d,
  curvaAbc,
} from "@/lib/mock/dashboard-obra";

export default function DashboardPage() {
  const openBudgetModal = useUiStore((s) => s.openBudgetModal);
  const custoRealizado = formatMoneyMillionsParts(kpis.custoRealizado);
  const receitaContratada = formatMoneyMillionsParts(kpis.receitaContratada);

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
      <div className="mb-8">
        <ObrasVencidasAlert />
      </div>

      {/* F10.5 — Insights dos Agentes IA (gated pela flag ia-module-enabled). */}
      <div className="mb-8">
        <IaInsightsCard />
      </div>

      <div className="mb-6 border-t border-white/5 pt-7" />

      <div className="mb-6 flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="mb-1.75 flex items-center gap-2.75">
            <h1 className="text-[27px] font-extrabold tracking-tight">Visão Geral</h1>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-success/12 px-2.75 py-1 text-xs font-semibold text-success">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              Em andamento
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Resumo financeiro e físico da obra · atualizado há 8 min
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-0.75 rounded-lg border border-white/6 bg-muted p-0.75">
            <button type="button" className="rounded-md px-3.5 py-1.5 text-[13px] font-semibold text-muted-foreground">
              Mês
            </button>
            <button type="button" className="rounded-md bg-[#33384a] px-3.5 py-1.5 text-[13px] font-semibold text-foreground">
              Trimestre
            </button>
            <button type="button" className="rounded-md px-3.5 py-1.5 text-[13px] font-semibold text-muted-foreground">
              Obra
            </button>
          </div>
          <button
            type="button"
            onClick={openBudgetModal}
            className="flex items-center gap-2 rounded-lg bg-primary px-4.25 py-2.5 text-[13.5px] font-bold text-primary-foreground shadow-[0_4px_14px_rgba(255,107,107,0.28)] hover:bg-primary-hover"
          >
            <Plus className="h-4.25 w-4.25" />
            Novo Orçamento
          </button>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-4 gap-4">
        <KpiCard
          label="Custo Realizado"
          value={custoRealizado.value}
          unit={custoRealizado.unit}
          icon={TrendingDown}
          iconClassName="text-secondary"
          iconBgClassName="bg-secondary/14"
          deltaDirection="down"
          deltaText="5,5%"
          helperText={`vs. previsto ${formatMoneyMillionsParts(kpis.custoPrevisto).value} mi`}
        />
        <KpiCard
          label="Receita Contratada"
          value={receitaContratada.value}
          unit={receitaContratada.unit}
          icon={FileSignature}
          iconClassName="text-success"
          iconBgClassName="bg-success/14"
          deltaDirection="up"
          deltaText={formatMoneyRounded(kpis.aditivos)}
          helperText="em aditivos"
        />
        <KpiCard
          label="Margem Bruta"
          value={formatPercent(kpis.margemBrutaPct).replace("%", "")}
          unit="%"
          icon={Percent}
          iconClassName="text-success"
          iconBgClassName="bg-success/14"
          deltaDirection="up"
          deltaText={`${formatPercent(kpis.margemVarPp).replace("%", "")} p.p.`}
          helperText="vs. mês anterior"
        />
        <KpiCard
          label="Avanço Físico"
          value={String(kpis.avancoFisicoPct)}
          unit="%"
          icon={AlertTriangle}
          iconClassName="text-primary"
          iconBgClassName="bg-primary/16"
          warn
          progressPct={kpis.avancoFisicoPct}
          progressMarkerPct={obraAtual.avancoPrevistoPct}
          deltaDirection="down"
          deltaText={`${kpis.desvioAvancoPp} p.p.`}
          helperText={`abaixo do previsto (${obraAtual.avancoPrevistoPct}%)`}
        />
      </div>

      <div className="mb-4 grid grid-cols-[1fr_340px] gap-4">
        <div className="rounded-[10px] border border-white/5 bg-card px-5 pt-5 pb-4 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
          <div className="mb-1.5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="mb-0.75 text-base font-bold">Curva S — Previsto x Realizado</h3>
              <p className="text-[13px] text-muted-foreground">
                Avanço acumulado · passe o mouse para valores exatos
              </p>
            </div>
            <div className="flex items-center gap-4.5">
              <span className="inline-flex items-center gap-1.75 text-[12.5px] font-semibold text-subtle-foreground">
                <span className="inline-block h-0.75 w-3.5 rounded-sm bg-secondary" />
                Previsto
              </span>
              <span className="inline-flex items-center gap-1.75 text-[12.5px] font-semibold text-subtle-foreground">
                <span className="inline-block h-0.75 w-3.5 rounded-sm bg-success" />
                Realizado
              </span>
            </div>
          </div>
          <CurvaSChart
            previsto={curvaSPrevisto}
            realizado={curvaSRealizado}
            meses={curvaSMeses}
            baseMilhoes={curvaSBaseMilhoes}
          />
        </div>

        <StatusObraCard obra={obraAtual} />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4">
        <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
          <div className="mb-3.5 flex items-start justify-between">
            <div>
              <h3 className="mb-0.75 text-base font-bold">Fluxo de Caixa Diário</h3>
              <p className="text-[13px] text-muted-foreground">Saldo líquido · últimos 15 dias úteis</p>
            </div>
            <div className="flex gap-4 text-right">
              <div>
                <div className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">Entradas</div>
                <div className="font-mono text-[15px] font-bold text-success">R$ {fluxoEntradasMi.toFixed(2).replace(".", ",")} mi</div>
              </div>
              <div>
                <div className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">Saídas</div>
                <div className="font-mono text-[15px] font-bold text-primary">R$ {fluxoSaidasMi.toFixed(2).replace(".", ",")} mi</div>
              </div>
            </div>
          </div>
          <FluxoCaixaChart valoresDiarios={fluxoCaixaDiario} />
        </div>

        <ContasList contas={contasPagarReceber} aReceber7d={aReceber7d} aPagar7d={aPagar7d} />
      </div>

      <CurvaAbcCard itens={curvaAbc} />

      <BudgetModal />
      <ImportSpreadsheetModal />
    </>
  );
}
