"use client";

import { useState } from "react";
import { smoothPath } from "@/lib/svg-path";

interface CurvaSChartProps {
  previsto: number[];
  realizado: number[];
  meses: string[];
  baseMilhoes: number;
}

const W = 760;
const H = 300;
const L = 46;
const R = 18;
const T = 18;
const B = 34;
const PLOT_W = W - L - R;
const PLOT_H = H - T - B;

export function CurvaSChart({ previsto, realizado, meses, baseMilhoes }: CurvaSChartProps) {
  const [hover, setHover] = useState<number | null>(null);

  const x = (i: number) => L + (i / (meses.length - 1)) * PLOT_W;
  const y = (pct: number) => T + (1 - pct / 100) * PLOT_H;

  const prevPts: [number, number][] = previsto.map((p, i) => [x(i), y(p)]);
  const realPts: [number, number][] = realizado.map((p, i) => [x(i), y(p)]);
  const prevLine = smoothPath(prevPts);
  const realLine = smoothPath(realPts);
  const prevArea = `${prevLine} L ${x(previsto.length - 1)} ${T + PLOT_H} L ${x(0)} ${T + PLOT_H} Z`;
  const realArea = `${realLine} L ${x(realizado.length - 1)} ${T + PLOT_H} L ${x(0)} ${T + PLOT_H} Z`;

  const stepHalf = PLOT_W / (meses.length - 1) / 2;
  const flipTooltip = hover !== null && x(hover) > W / 2;
  const tooltipW = 210;
  const tooltipH = 80;
  const tooltipX = hover !== null ? (flipTooltip ? x(hover) - tooltipW - 12 : x(hover) + 12) : 0;
  const tooltipY = T + 6;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-1.5 block w-full">
      <defs>
        <linearGradient id="gp" x1={0} y1={0} x2={0} y2={1}>
          <stop offset="0%" stopColor="#845ef7" stopOpacity={0.28} />
          <stop offset="100%" stopColor="#845ef7" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="gr" x1={0} y1={0} x2={0} y2={1}>
          <stop offset="0%" stopColor="#38d9a9" stopOpacity={0.3} />
          <stop offset="100%" stopColor="#38d9a9" stopOpacity={0} />
        </linearGradient>
      </defs>

      {[0, 25, 50, 75, 100].map((g) => (
        <g key={g}>
          <line x1={L} y1={y(g)} x2={W - R} y2={y(g)} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
          <text x={L - 10} y={y(g) + 4} textAnchor="end" fill="#5b6072" fontSize={11} fontFamily="var(--font-geist-mono)">
            {g}%
          </text>
        </g>
      ))}

      {meses.map((m, i) => (
        <text key={m} x={x(i)} y={H - 12} textAnchor="middle" fill="#5b6072" fontSize={11}>
          {m}
        </text>
      ))}

      <path d={prevArea} fill="url(#gp)" />
      <path d={realArea} fill="url(#gr)" />
      <path d={prevLine} fill="none" stroke="#845ef7" strokeWidth={2.5} strokeDasharray="6 5" strokeLinecap="round" />
      <path d={realLine} fill="none" stroke="#38d9a9" strokeWidth={2.5} strokeLinecap="round" />

      {hover !== null && (
        <>
          <line x1={x(hover)} y1={T} x2={x(hover)} y2={T + PLOT_H} stroke="rgba(255,255,255,0.18)" strokeWidth={1} strokeDasharray="3 3" />
          <circle cx={x(hover)} cy={y(previsto[hover])} r={4.5} fill="#845ef7" stroke="#1f222c" strokeWidth={2} />
          {realizado[hover] != null && (
            <circle cx={x(hover)} cy={y(realizado[hover])} r={4.5} fill="#38d9a9" stroke="#1f222c" strokeWidth={2} />
          )}
          <g>
            <rect x={tooltipX} y={tooltipY} width={tooltipW} height={tooltipH} rx={8} fill="#15171e" stroke="rgba(255,255,255,0.12)" strokeWidth={1} />
            <text x={tooltipX + 13} y={tooltipY + 22} fill="#fff" fontSize={13} fontWeight={700}>
              {meses[hover]} / 2026
            </text>
            <circle cx={tooltipX + 17} cy={tooltipY + 42} r={4} fill="#845ef7" />
            <text x={tooltipX + 28} y={tooltipY + 46} fill="#b9bfce" fontSize={12}>
              Previsto
            </text>
            <text x={tooltipX + tooltipW - 13} y={tooltipY + 46} textAnchor="end" fill="#fff" fontSize={12} fontWeight={700} fontFamily="var(--font-geist-mono)">
              {previsto[hover]}% · {((previsto[hover] / 100) * baseMilhoes).toFixed(2).replace(".", ",")} mi
            </text>
            <circle cx={tooltipX + 17} cy={tooltipY + 63} r={4} fill="#38d9a9" />
            <text x={tooltipX + 28} y={tooltipY + 67} fill="#b9bfce" fontSize={12}>
              Realizado
            </text>
            <text x={tooltipX + tooltipW - 13} y={tooltipY + 67} textAnchor="end" fill="#fff" fontSize={12} fontWeight={700} fontFamily="var(--font-geist-mono)">
              {realizado[hover] != null
                ? `${realizado[hover]}% · ${((realizado[hover] / 100) * baseMilhoes).toFixed(2).replace(".", ",")} mi`
                : "—"}
            </text>
          </g>
        </>
      )}

      {meses.map((m, i) => (
        <rect
          key={`hit-${m}`}
          x={x(i) - stepHalf}
          y={T}
          width={stepHalf * 2}
          height={PLOT_H}
          fill="transparent"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
        />
      ))}
    </svg>
  );
}
