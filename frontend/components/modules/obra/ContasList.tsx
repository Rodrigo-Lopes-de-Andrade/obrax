import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import type { ContaPagarReceber } from "@/lib/types/orcamento";
import { formatMoneyRounded } from "@/lib/decimal";

interface ContasListProps {
  contas: ContaPagarReceber[];
  aReceber7d: number;
  aPagar7d: number;
}

export function ContasList({ contas, aReceber7d, aPagar7d }: ContasListProps) {
  return (
    <div className="rounded-[10px] border border-white/5 bg-card p-5 shadow-[0_2px_10px_rgba(0,0,0,0.22)]">
      <div className="mb-1.5 flex items-center justify-between">
        <h3 className="text-base font-bold">Contas a Pagar / Receber</h3>
        <span className="cursor-pointer text-[12.5px] font-semibold text-muted-foreground">Ver tudo</span>
      </div>

      <div className="mt-3 mb-1 flex gap-2.5">
        <div className="flex-1 rounded-lg border border-success/18 bg-success/10 px-3.25 py-2.75">
          <div className="text-[11.5px] font-bold tracking-wide text-success uppercase">A receber · 7d</div>
          <div className="mt-0.5 font-mono text-lg font-extrabold">{formatMoneyRounded(aReceber7d)}</div>
        </div>
        <div className="flex-1 rounded-lg border border-primary/18 bg-primary/10 px-3.25 py-2.75">
          <div className="text-[11.5px] font-bold tracking-wide text-primary uppercase">A pagar · 7d</div>
          <div className="mt-0.5 font-mono text-lg font-extrabold">{formatMoneyRounded(aPagar7d)}</div>
        </div>
      </div>

      <div className="mt-2 flex flex-col">
        {contas.map((conta) => {
          const isReceber = conta.tipo === "receber";
          const Icon = isReceber ? ArrowDownLeft : ArrowUpRight;
          const colorClass = isReceber ? "text-success" : "text-primary";
          const bgClass = isReceber ? "bg-success/14" : "bg-primary/14";
          const sinal = isReceber ? "+" : "−";
          return (
            <div
              key={conta.id}
              className="flex items-center gap-3 rounded-md border-b border-white/4 px-2 py-2.5 hover:bg-white/2.5"
            >
              <div className={`flex h-7.5 w-7.5 flex-shrink-0 items-center justify-center rounded-lg ${bgClass}`}>
                <Icon className={`h-3.75 w-3.75 ${colorClass}`} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13.5px] font-semibold">{conta.titulo}</div>
                <div className="text-xs text-muted-foreground">{conta.vencimento}</div>
              </div>
              <div className={`font-mono text-[13.5px] font-bold whitespace-nowrap ${colorClass}`}>
                {sinal} {formatMoneyRounded(conta.valor)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
