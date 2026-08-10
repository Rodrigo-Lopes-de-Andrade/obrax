"use client";

import Link from "next/link";
import { Building2, ChevronRight, Plus } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/modules/obra/status";
import { formatDate, formatMoney } from "@/lib/format";
import { useObras } from "@/lib/hooks/use-obras";

/** Painel "Suas obras" do dashboard (F4.1) — dados reais via GET /obras.
 *
 * Substitui a antiga "Visão Geral" (Curva S / fluxo de caixa / curva ABC), que
 * era 100% demo: o backend não expõe esses agregados por obra hoje. Aqui
 * mostramos só o que existe de verdade — status, valor de contrato e prazo. */
export function ObrasResumoCard() {
  const { data, isLoading } = useObras({ limit: 8 });
  const obras = data?.items ?? [];

  return (
    <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <div className="mb-3.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/14">
            <Building2 className="h-[17px] w-[17px] text-secondary" />
          </div>
          <div>
            <h3 className="text-base font-bold">Suas obras</h3>
            <p className="text-[13px] text-muted-foreground">
              Obras mais recentes e seu andamento
            </p>
          </div>
        </div>
        <Link
          href="/obras"
          className="inline-flex items-center gap-1 text-[13px] font-semibold text-primary hover:underline"
        >
          Ver todas
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : obras.length === 0 ? (
        <div className="rounded-lg border border-white/5 bg-muted/40 px-6 py-12 text-center">
          <span className="mx-auto grid size-11 place-items-center rounded-lg bg-white/6 text-muted-foreground">
            <Building2 className="size-5" />
          </span>
          <h4 className="mt-4 font-semibold">Nenhuma obra ainda</h4>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            Cadastre sua primeira obra para acompanhar prazos e valores por aqui.
          </p>
          <Link
            href="/obras"
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-[13.5px] font-bold text-primary-foreground hover:bg-primary-hover"
          >
            <Plus className="h-4 w-4" />
            Nova obra
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-white/5">
          {obras.map((o) => (
            <li key={o.id}>
              <Link
                href={`/obras/${o.id}/documentos`}
                className="group flex items-center justify-between gap-3 py-3 transition-colors hover:bg-white/2"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[12px] text-muted-foreground">{o.codigo}</span>
                    <span className="truncate text-sm font-semibold">{o.nome}</span>
                  </div>
                  <span className="text-[12.5px] text-muted-foreground">
                    {o.valor_contrato ? formatMoney(o.valor_contrato) : "Sem valor de contrato"}
                    {o.data_prevista_fim ? ` · previsão ${formatDate(o.data_prevista_fim)}` : ""}
                  </span>
                </div>
                <div className="flex flex-shrink-0 items-center gap-3">
                  <StatusBadge status={o.status} />
                  <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
