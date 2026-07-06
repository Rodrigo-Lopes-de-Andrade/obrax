import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  unit?: string;
  icon: LucideIcon;
  iconClassName: string;
  iconBgClassName: string;
  deltaDirection?: "up" | "down";
  deltaText?: string;
  helperText?: string;
  progressPct?: number;
  progressMarkerPct?: number;
  warn?: boolean;
}

export function KpiCard({
  label,
  value,
  unit,
  icon: Icon,
  iconClassName,
  iconBgClassName,
  deltaDirection,
  deltaText,
  helperText,
  progressPct,
  progressMarkerPct,
  warn,
}: KpiCardProps) {
  const DeltaIcon = deltaDirection === "down" ? ArrowDownRight : ArrowUpRight;
  const deltaColor = deltaDirection === "down" && !warn ? "text-success" : warn ? "text-primary" : "text-success";

  return (
    <div
      className={cn(
        "rounded-[10px] border bg-card p-[18px] shadow-[0_2px_10px_rgba(0,0,0,0.22)] transition-[box-shadow,transform,border-color] hover:-translate-y-0.5 hover:border-white/10 hover:shadow-[0_10px_28px_rgba(0,0,0,0.34)]",
        warn ? "border-primary/20" : "border-white/5",
      )}
    >
      <div className="mb-3.5 flex items-center justify-between">
        <span className="text-[11px] font-bold tracking-[0.07em] text-muted-foreground uppercase">
          {label}
        </span>
        <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", iconBgClassName)}>
          <Icon className={cn("h-[17px] w-[17px]", iconClassName)} />
        </div>
      </div>

      <div className="font-mono text-[27px] font-extrabold tracking-tight whitespace-nowrap">
        {value}
        {unit && <span className="text-[15px] font-semibold text-muted-foreground"> {unit}</span>}
      </div>

      {progressPct !== undefined ? (
        <div className="relative mt-[11px] h-1.5 overflow-hidden rounded-full bg-white/8">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-primary"
            style={{ width: `${progressPct}%` }}
          />
          {progressMarkerPct !== undefined && (
            <div
              className="absolute -top-[3px] -bottom-[3px] w-0.5 bg-white/55"
              style={{ left: `${progressMarkerPct}%` }}
            />
          )}
        </div>
      ) : null}

      {(deltaText || helperText) && (
        <div className="mt-2.5 flex items-center gap-1.5 text-[12.5px]">
          {deltaText && (
            <span className={cn("inline-flex items-center gap-0.5 font-bold", deltaColor)}>
              <DeltaIcon className="h-3.5 w-3.5" />
              {deltaText}
            </span>
          )}
          {helperText && <span className="text-muted-foreground">{helperText}</span>}
        </div>
      )}
    </div>
  );
}
