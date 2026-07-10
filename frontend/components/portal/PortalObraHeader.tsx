import type { ObraStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<ObraStatus, string> = {
  planejamento: "Em planejamento",
  execucao: "Em execução",
  pausada: "Pausada",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

const STATUS_STYLE: Record<ObraStatus, string> = {
  planejamento: "bg-muted text-muted-foreground",
  execucao: "bg-primary/15 text-primary",
  pausada: "bg-amber-500/15 text-amber-500",
  concluida: "bg-success/15 text-success",
  cancelada: "bg-destructive/15 text-destructive",
};

/** Cabeçalho da obra no portal: marca da construtora + identificação + status. */
export function PortalObraHeader({
  construtora,
  nome,
  codigo,
  status,
}: {
  construtora: string;
  nome: string;
  codigo: string;
  status: ObraStatus;
}) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {construtora}
      </p>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <h1 className="text-2xl font-extrabold tracking-tight">{nome}</h1>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
            STATUS_STYLE[status],
          )}
        >
          {STATUS_LABEL[status]}
        </span>
      </div>
      <p className="mt-0.5 text-sm text-muted-foreground">Obra {codigo}</p>
    </div>
  );
}
