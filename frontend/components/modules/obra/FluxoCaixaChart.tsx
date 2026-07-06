"use client";

import { useState } from "react";

interface FluxoCaixaChartProps {
  valoresDiarios: number[];
}

const W = 440;
const H = 200;
const L = 34;
const R = 10;
const T = 14;
const B = 26;
const PLOT_W = W - L - R;
const PLOT_H = H - T - B;
const MAX_ABS = 70;

export function FluxoCaixaChart({ valoresDiarios }: FluxoCaixaChartProps) {
  const [hover, setHover] = useState<number | null>(null);

  const zeroY = T + PLOT_H * (MAX_ABS / (MAX_ABS * 2));
  const n = valoresDiarios.length;
  const slot = PLOT_W / n;
  const barWidth = slot * 0.52;

  const hoverValue = hover !== null ? valoresDiarios[hover] : null;
  const hoverCx = hover !== null ? L + slot * hover + slot / 2 : 0;
  const flipTooltip = hoverCx > W / 2;
  const tooltipW = 120;
  const tooltipX = Math.max(2, Math.min(W - tooltipW - 2, flipTooltip ? hoverCx - tooltipW : hoverCx));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block w-full">
      <line x1={L} y1={zeroY} x2={W - R} y2={zeroY} stroke="rgba(255,255,255,0.12)" strokeWidth={1} />

      {valoresDiarios.map((v, i) => {
        const cx = L + slot * i + slot / 2;
        const barHeight = Math.max((Math.abs(v) / (MAX_ABS * 2)) * PLOT_H, 1.5);
        const barY = v >= 0 ? zeroY - barHeight : zeroY;
        const color = v >= 0 ? "#38d9a9" : "#ff6b6b";
        return (
          <rect
            key={i}
            x={cx - barWidth / 2}
            y={barY}
            width={barWidth}
            height={barHeight}
            rx={3}
            fill={color}
            opacity={hover === null || hover === i ? 1 : 0.4}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        );
      })}

      {[1, 5, 10, 15].map((d) => {
        const cx = L + slot * (d - 1) + slot / 2;
        return (
          <text key={d} x={cx} y={H - 8} textAnchor="middle" fill="#5b6072" fontSize={10} fontFamily="var(--font-geist-mono)">
            D{d}
          </text>
        );
      })}

      {hoverValue !== null && (
        <g>
          <rect x={tooltipX} y={4} width={tooltipW} height={42} rx={7} fill="#15171e" stroke="rgba(255,255,255,0.12)" />
          <text x={tooltipX + 11} y={21} fill="#8c92a4" fontSize={11}>
            Dia útil {hover! + 1}
          </text>
          <text
            x={tooltipX + 11}
            y={37}
            fill={hoverValue >= 0 ? "#38d9a9" : "#ff6b6b"}
            fontSize={13}
            fontWeight={700}
            fontFamily="var(--font-geist-mono)"
          >
            {hoverValue >= 0 ? "+" : "−"}R$ {Math.abs(hoverValue)}k
          </text>
        </g>
      )}
    </svg>
  );
}
