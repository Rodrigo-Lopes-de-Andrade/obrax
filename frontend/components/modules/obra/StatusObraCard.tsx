import { CalendarClock, Layers, UsersRound } from "lucide-react";
import { ProgressRing } from "@/components/shared/ProgressRing";
import type { obraAtual } from "@/lib/mock/dashboard-obra";

interface StatusObraCardProps {
  obra: typeof obraAtual;
}

export function StatusObraCard({ obra }: StatusObraCardProps) {
  return (
    <div className="flex flex-col rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <h3 className="mb-1 text-base font-bold">Status da Obra</h3>
      <p className="mb-4.5 text-[13px] text-muted-foreground">
        {obra.nome} · {obra.unidades} unidades
      </p>

      <div className="mb-4.5 flex items-center justify-center">
        <ProgressRing pct={obra.avancoFisicoPct} label="concluído" />
      </div>

      <div className="flex flex-col gap-3.25">
        <StatusRow icon={CalendarClock} label="Entrega prevista" value={obra.entregaPrevista}>
          <span className="rounded-full bg-primary/12 px-2.25 py-0.75 text-xs font-bold text-primary">
            {obra.diasAtraso} dias atraso
          </span>
        </StatusRow>
        <StatusRow icon={Layers} label="Etapa atual" value={obra.etapaAtual} />
        <StatusRow icon={UsersRound} label="Equipe no canteiro" value={`${obra.equipeCanteiro} colaboradores`} />
      </div>
    </div>
  );
}

function StatusRow({
  icon: Icon,
  label,
  value,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.75">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-sm font-semibold">{value}</div>
      </div>
      {children}
    </div>
  );
}
