import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { OrcamentoStatus } from "@/lib/api/types";

const STATUS_META: Record<OrcamentoStatus, { label: string; dot: string }> = {
  rascunho: { label: "Rascunho", dot: "bg-muted-foreground" },
  em_revisao: { label: "Em revisão", dot: "bg-sky-400" },
  aguardando_aprovacao: { label: "Aguardando aprovação", dot: "bg-amber-400" },
  aprovado: { label: "Aprovado", dot: "bg-emerald-400" },
  rejeitado: { label: "Rejeitado", dot: "bg-destructive" },
};

/** Opções na ordem do enum `orcamento_status` (backend). */
export const ORCAMENTO_STATUS_OPTIONS = (
  Object.keys(STATUS_META) as OrcamentoStatus[]
).map((value) => ({ value, label: STATUS_META[value].label }));

export function orcamentoStatusLabel(status: OrcamentoStatus): string {
  return STATUS_META[status].label;
}

/** Máquina de estados (espelho do backend). */
const TRANSICOES: Record<OrcamentoStatus, OrcamentoStatus[]> = {
  rascunho: ["em_revisao", "aguardando_aprovacao"],
  em_revisao: ["rascunho", "aguardando_aprovacao"],
  aguardando_aprovacao: ["aprovado", "rejeitado", "em_revisao"],
  rejeitado: ["rascunho", "em_revisao"],
  aprovado: [],
};

/** Status atual + destinos válidos — para popular o seletor sem oferecer
 * transições que o backend rejeitaria (409). */
export function nextStatuses(current: OrcamentoStatus): OrcamentoStatus[] {
  return [current, ...TRANSICOES[current]];
}

export function OrcamentoStatusBadge({ status }: { status: OrcamentoStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="outline" className="gap-1.5 font-normal whitespace-nowrap">
      <span className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  );
}
