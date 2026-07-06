import type { ItemAbc } from "@/lib/types/orcamento";
import { formatMoneyRounded } from "@/lib/decimal";

const CLASSE_COLOR: Record<ItemAbc["classe"], { color: string; bg: string }> = {
  A: { color: "var(--color-secondary)", bg: "rgba(132,94,247,0.16)" },
  B: { color: "var(--chart-4)", bg: "rgba(92,124,250,0.16)" },
  C: { color: "var(--muted-foreground)", bg: "rgba(140,146,164,0.16)" },
};

interface CurvaAbcListProps {
  itens: ItemAbc[];
  showHeader?: boolean;
}

export function CurvaAbcList({ itens, showHeader }: CurvaAbcListProps) {
  return (
    <div className="flex flex-col gap-0.75">
      {showHeader && (
        <div className="grid grid-cols-[24px_1.6fr_2.4fr_96px_130px] gap-3.5 border-b border-white/5 px-2 pb-2.5 text-[11px] font-bold tracking-wide text-[#5b6072] uppercase">
          <div>Cl.</div>
          <div>Insumo</div>
          <div>% acumulado do custo</div>
          <div className="text-right">% custo</div>
          <div className="text-right">Valor</div>
        </div>
      )}
      {itens.map((item, i) => {
        const { color, bg } = CLASSE_COLOR[item.classe];
        return (
          <div
            key={i}
            className={`grid grid-cols-[24px_1.6fr_2.4fr_96px_130px] items-center gap-3.5 rounded-md px-2 ${
              showHeader ? "py-2.75" : "border-b border-white/4 py-3"
            }`}
          >
            <div
              className="flex h-5.5 w-5.5 items-center justify-center rounded-md text-[11px] font-extrabold"
              style={{ color, background: bg }}
            >
              {item.classe}
            </div>
            <div className="truncate text-[13.5px] font-semibold">{item.nome}</div>
            <div className="relative h-2 overflow-hidden rounded-full bg-white/6">
              <div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{ width: `${item.pctAcumulado}%`, background: color }}
              />
            </div>
            <div className="text-right font-mono text-[13px] font-bold">{item.pct}%</div>
            <div className="text-right font-mono text-[13px] font-semibold text-subtle-foreground">
              {formatMoneyRounded(item.valor)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
