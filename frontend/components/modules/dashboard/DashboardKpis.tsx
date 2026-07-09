"use client";

import { Building2, FileClock, MessageSquareWarning, Wallet } from "lucide-react";

import { KpiCard } from "@/components/shared/KpiCard";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoneyMillionsParts } from "@/lib/decimal";
import { useDashboardSummary } from "@/lib/hooks/use-dashboard";

/** Faixa de KPIs da empresa, alimentada por GET /dashboard/summary (B4.4/F4.1). */
export function DashboardKpis() {
  const { data, isLoading, isError } = useDashboardSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[132px] rounded-[10px]" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-[10px] border border-primary/20 bg-primary/5 px-5 py-4 text-sm text-muted-foreground">
        Não foi possível carregar os indicadores. Tente novamente.
      </div>
    );
  }

  const valor = formatMoneyMillionsParts(data.obras_valor_total);

  return (
    <div className="grid grid-cols-4 gap-4">
      <KpiCard
        label="Obras Ativas"
        value={String(data.obras_ativas)}
        icon={Building2}
        iconClassName="text-secondary"
        iconBgClassName="bg-secondary/14"
        helperText="em execução ou planejamento"
      />
      <KpiCard
        label="Valor Contratado"
        value={valor.value}
        unit={valor.unit}
        icon={Wallet}
        iconClassName="text-success"
        iconBgClassName="bg-success/14"
        helperText="somatório das obras ativas"
      />
      <KpiCard
        label="Tickets Abertos"
        value={String(data.tickets_abertos)}
        icon={MessageSquareWarning}
        iconClassName="text-primary"
        iconBgClassName="bg-primary/16"
        warn={data.tickets_abertos > 0}
        helperText="aguardando atendimento"
      />
      <KpiCard
        label="Orçamentos Pendentes"
        value={String(data.orcamentos_pendentes)}
        icon={FileClock}
        iconClassName="text-subtle-foreground"
        iconBgClassName="bg-white/6"
        helperText="em análise"
      />
    </div>
  );
}
