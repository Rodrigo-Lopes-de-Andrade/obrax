"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import { useObras } from "@/lib/hooks/use-obras";
import type { Obra } from "@/lib/api/types";

const ATIVA = (o: Obra) => o.status !== "concluida" && o.status !== "cancelada";

/** Obras com `data_prevista_fim` no passado e ainda em andamento. */
function vencidas(obras: Obra[]): Obra[] {
  const hoje = new Date().toISOString().slice(0, 10);
  return obras
    .filter((o) => ATIVA(o) && o.data_prevista_fim !== null && o.data_prevista_fim < hoje)
    .sort((a, b) => (a.data_prevista_fim! < b.data_prevista_fim! ? -1 : 1));
}

/** AlertList do dashboard (F4.1): obras com prazo estourado. */
export function ObrasVencidasAlert() {
  const { data, isLoading } = useObras({ limit: 100 });

  return (
    <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <div className="mb-3.5 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/16">
          <AlertTriangle className="h-[17px] w-[17px] text-primary" />
        </div>
        <div>
          <h3 className="text-base font-bold">Obras com prazo vencido</h3>
          <p className="text-[13px] text-muted-foreground">
            Previsão de término já passou e a obra segue ativa
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : (
        <AlertRows obras={vencidas(data?.items ?? [])} />
      )}
    </div>
  );
}

function AlertRows({ obras }: { obras: Obra[] }) {
  if (obras.length === 0) {
    return (
      <div className="flex items-center gap-2.5 rounded-lg bg-success/8 px-4 py-3.5 text-sm text-subtle-foreground">
        <CheckCircle2 className="h-4.5 w-4.5 text-success" />
        Nenhuma obra com prazo vencido. Tudo em dia.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-white/5">
      {obras.slice(0, 6).map((o) => (
        <li key={o.id}>
          <Link
            href={`/obras/${o.id}/documentos`}
            className="group flex items-center justify-between gap-3 py-2.75 transition-colors hover:bg-white/2"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] text-muted-foreground">{o.codigo}</span>
                <span className="truncate text-sm font-semibold">{o.nome}</span>
              </div>
              <span className="text-[12.5px] text-primary">
                Venceu em {formatDate(o.data_prevista_fim)}
              </span>
            </div>
            <ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
