import { cronograma, cronogramaMeses } from "@/lib/mock/dashboard-obra";

export function CronogramaTab() {
  return (
    <div className="overflow-hidden rounded-[10px] border border-white/6">
      <div className="grid grid-cols-[200px_1fr] border-b border-white/6 bg-card">
        <div className="px-3.5 py-2.75 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
          Etapa
        </div>
        <div className="grid grid-cols-8">
          {cronogramaMeses.map((mes) => (
            <div key={mes} className="py-2.75 text-center text-[11px] font-bold text-muted-foreground">
              {mes}
            </div>
          ))}
        </div>
      </div>

      {cronograma.map((grupo) => (
        <div key={grupo.etapa} className="grid grid-cols-[200px_1fr] items-center border-b border-white/4">
          <div className="px-3.5 py-3 text-[13px] font-semibold">{grupo.etapa}</div>
          <div className="relative mx-2 h-8.5">
            <div
              className="absolute top-2.25 h-4 rounded-md"
              style={{ left: `${grupo.startPct}%`, width: `${grupo.widthPct}%`, background: grupo.color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
