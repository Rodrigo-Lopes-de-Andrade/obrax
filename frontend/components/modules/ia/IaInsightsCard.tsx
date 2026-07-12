"use client";

import Link from "next/link";
import { Bot, Clock, Gauge, Sparkles } from "lucide-react";

import { FeatureFlag } from "@/components/shared/FeatureFlag";
import { Skeleton } from "@/components/ui/skeleton";
import { useIaInsights } from "@/lib/hooks/use-ia";

function fmtHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Insights de IA no dashboard (F10.5, US-24). Só aparece com a flag ligada. */
export function IaInsightsCard() {
  return (
    <FeatureFlag flag="ia-module-enabled">
      <IaInsightsInner />
    </FeatureFlag>
  );
}

function IaInsightsInner() {
  const { data, isLoading } = useIaInsights();

  return (
    <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary/12 text-primary">
            <Bot className="size-4.5" />
          </span>
          <div>
            <h3 className="text-base font-bold leading-tight">Agentes IA</h3>
            <p className="text-[12.5px] text-muted-foreground">Atividade dos assistentes no WhatsApp</p>
          </div>
        </div>
        <Link href="/ia/auditoria" className="text-xs font-medium text-primary hover:underline">
          Ver auditoria
        </Link>
      </div>

      {isLoading || !data ? (
        <Skeleton className="h-24 w-full rounded-lg" />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Stat
              icon={Sparkles}
              value={String(data.acoes_ultima_semana)}
              label="ações · 7 dias"
            />
            <Stat
              icon={Clock}
              value={`${data.economia_tempo_min} min`}
              label="economia média"
            />
            <Stat
              icon={Gauge}
              value={`${Math.round(data.taxa_sucesso * 100)}%`}
              label="taxa de sucesso"
            />
          </div>

          {data.ultimas_acoes.length > 0 ? (
            <div className="mt-4 space-y-1.5">
              <p className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
                Últimas ações
              </p>
              {data.ultimas_acoes.slice(0, 3).map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-sm">
                  <span className="flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-foreground">
                    {a.agent ?? "ia"}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-muted-foreground" title={a.command}>
                    {a.command}
                  </span>
                  <span className="flex-shrink-0 text-xs text-muted-foreground">
                    {fmtHora(a.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function Stat({
  icon: Icon,
  value,
  label,
}: {
  icon: typeof Bot;
  value: string;
  label: string;
}) {
  return (
    <div className="rounded-lg border border-white/5 bg-muted/40 p-3">
      <Icon className="size-4 text-primary" />
      <div className="mt-1.5 text-xl font-extrabold tracking-tight tabular-nums">{value}</div>
      <div className="text-[11.5px] text-muted-foreground">{label}</div>
    </div>
  );
}
