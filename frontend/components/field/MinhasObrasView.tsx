"use client";

import Link from "next/link";
import { ChevronRight, Building2 } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import type { ObraStatus } from "@/lib/api/types";
import { useObras } from "@/lib/hooks/use-obras";
import { useFieldStore } from "@/state/field";

const STATUS_LABEL: Record<ObraStatus, string> = {
  planejamento: "Planejamento",
  execucao: "Execução",
  pausada: "Pausada",
  concluida: "Concluída",
  cancelada: "Cancelada",
};
const STATUS_COR: Record<ObraStatus, string> = {
  planejamento: "#6366f1",
  execucao: "#059669",
  pausada: "#d97706",
  concluida: "#0ea5e9",
  cancelada: "#dc2626",
};

/** Obras ativas primeiro (é o que interessa em campo). */
const ORDEM: ObraStatus[] = ["execucao", "planejamento", "pausada", "concluida", "cancelada"];

export function MinhasObrasView() {
  const { data, isLoading, isError } = useObras({ limit: 100 });
  const setLastObra = useFieldStore((s) => s.setLastObra);

  const obras = (data?.items ?? [])
    .slice()
    .sort((a, b) => ORDEM.indexOf(a.status) - ORDEM.indexOf(b.status));

  return (
    <div>
      <h1 className="mb-1 text-2xl font-extrabold tracking-tight">Minhas obras</h1>
      <p className="mb-4 text-sm text-muted-foreground">
        Toque em uma obra para abrir o checklist do dia
      </p>

      {isLoading ? (
        <div className="space-y-2.5">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-6 text-center text-sm text-muted-foreground">
          Não foi possível carregar as obras.
        </div>
      ) : obras.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-border px-4 py-10 text-center">
          <Building2 className="size-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">Nenhuma obra atribuída.</p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {obras.map((obra) => (
            <li key={obra.id}>
              <Link
                href={`/campo/checklist/${obra.id}`}
                onClick={() => setLastObra(obra.id)}
                className="flex min-h-[64px] items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 active:bg-muted"
              >
                <span
                  className="mt-0.5 size-2.5 flex-shrink-0 rounded-full"
                  style={{ background: STATUS_COR[obra.status] }}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{obra.nome}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {obra.codigo} · {STATUS_LABEL[obra.status]}
                  </div>
                </div>
                <ChevronRight className="size-5 flex-shrink-0 text-muted-foreground" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
