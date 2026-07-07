import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ObraStatus } from "@/lib/api/types";

const STATUS_META: Record<ObraStatus, { label: string; dot: string }> = {
  planejamento: { label: "Planejamento", dot: "bg-sky-400" },
  execucao: { label: "Execução", dot: "bg-primary" },
  pausada: { label: "Pausada", dot: "bg-amber-400" },
  concluida: { label: "Concluída", dot: "bg-emerald-400" },
  cancelada: { label: "Cancelada", dot: "bg-destructive" },
};

/** Opções na ordem do enum `obra_status` (backend) — para selects/filtros. */
export const OBRA_STATUS_OPTIONS = (
  Object.keys(STATUS_META) as ObraStatus[]
).map((value) => ({ value, label: STATUS_META[value].label }));

export function statusLabel(status: ObraStatus): string {
  return STATUS_META[status].label;
}

export function StatusBadge({ status }: { status: ObraStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="outline" className="gap-1.5 font-normal">
      <span className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  );
}
