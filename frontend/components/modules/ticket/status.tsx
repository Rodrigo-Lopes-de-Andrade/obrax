import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TicketStatus } from "@/lib/api/types";

const STATUS_META: Record<TicketStatus, { label: string; dot: string }> = {
  aberto: { label: "Aberto", dot: "bg-primary" },
  andamento: { label: "Em andamento", dot: "bg-sky-400" },
  resolvido: { label: "Resolvido", dot: "bg-emerald-400" },
  fechado: { label: "Fechado", dot: "bg-muted-foreground" },
};

/** Opções na ordem do enum `ticket_status` (backend) — para selects/filtros. */
export const TICKET_STATUS_OPTIONS = (
  Object.keys(STATUS_META) as TicketStatus[]
).map((value) => ({ value, label: STATUS_META[value].label }));

export function ticketStatusLabel(status: TicketStatus): string {
  return STATUS_META[status].label;
}

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="outline" className="gap-1.5 font-normal">
      <span className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  );
}
