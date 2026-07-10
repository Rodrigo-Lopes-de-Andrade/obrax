"use client";

import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AbcClasse, AbcClasseNome, AbcItem, CurvaAbc } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/format";
import { useCurvaAbc } from "@/lib/hooks/use-orcamentos";

// Cores A=vermelho / B=amarelo / C=verde (critério F6.1; espelha o PDF do backend).
const CLASSE: Record<AbcClasseNome, { cor: string; label: string; faixa: string }> = {
  A: { cor: "#dc2626", label: "Classe A", faixa: "≈ 80% do custo" },
  B: { cor: "#d97706", label: "Classe B", faixa: "≈ 15% do custo" },
  C: { cor: "#059669", label: "Classe C", faixa: "≈ 5% do custo" },
};

/** Fração (Decimal string "0.8000") → largura CSS "80%" (ponto, não vírgula). */
function cssWidth(fraction: string | undefined): string {
  const n = Number(fraction ?? 0);
  return `${(Number.isNaN(n) ? 0 : n) * 100}%`;
}

export function BdiTab({ orcamentoId }: { orcamentoId: string }) {
  const query = useCurvaAbc(orcamentoId);

  if (query.isLoading) {
    return (
      <div className="space-y-4 pt-2">
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const curva = query.data;
  if (!curva || curva.itens.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm font-medium">Sem itens classificados</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          Adicione insumos na aba Estrutura para ver a curva ABC — a concentração de
          custo por item (regra 80/15/5).
        </p>
      </div>
    );
  }

  const resumo = new Map(curva.classes.map((c) => [c.classe, c]));

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto pb-2">
      <div>
        <h2 className="text-sm font-semibold">Curva ABC</h2>
        <p className="text-xs text-muted-foreground">
          Concentração de custo direto por insumo (regra 80/15/5). Custo total{" "}
          <span className="font-medium text-foreground">{formatMoney(curva.custo_total)}</span>.
        </p>
      </div>

      {/* Resumo por classe */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(["A", "B", "C"] as const).map((nome) => (
          <ClasseCard key={nome} nome={nome} classe={resumo.get(nome)} total={curva.custo_total} />
        ))}
      </div>

      {/* Pareto */}
      <div className="rounded-xl border border-border bg-card p-4">
        <ParetoChart curva={curva} />
      </div>

      {/* Tabela de itens ordenados por custo desc */}
      <div className="overflow-hidden rounded-xl border border-border">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10 text-center">Cl.</TableHead>
              <TableHead>Insumo</TableHead>
              <TableHead className="text-right">Custo</TableHead>
              <TableHead className="text-right">% custo</TableHead>
              <TableHead className="w-[34%]">% acumulado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {curva.itens.map((it) => (
              <ItemRow key={it.id} item={it} />
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function ClasseCard({
  nome,
  classe,
  total,
}: {
  nome: AbcClasseNome;
  classe: AbcClasse | undefined;
  total: string;
}) {
  const meta = CLASSE[nome];
  const count = classe?.count ?? 0;
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="flex size-6 items-center justify-center rounded-md text-xs font-bold text-white"
            style={{ background: meta.cor }}
          >
            {nome}
          </span>
          <span className="text-sm font-medium">{meta.label}</span>
        </div>
        <span className="text-xs text-muted-foreground">{meta.faixa}</span>
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <span className="text-lg font-semibold tabular-nums">{formatMoney(classe?.custo ?? "0")}</span>
        <span className="text-xs text-muted-foreground">
          {count} {count === 1 ? "item" : "itens"} · {formatPercent(classe?.pct ?? "0")}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full"
          style={{
            width: total && Number(total) > 0 ? cssWidth(classe?.pct) : "0%",
            background: meta.cor,
          }}
        />
      </div>
    </div>
  );
}

function ItemRow({ item }: { item: AbcItem }) {
  const meta = CLASSE[item.classe];
  return (
    <TableRow>
      <TableCell className="text-center">
        <span
          className="inline-flex size-5 items-center justify-center rounded text-[11px] font-bold text-white"
          style={{ background: meta.cor }}
        >
          {item.classe}
        </span>
      </TableCell>
      <TableCell>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium">{item.descricao}</span>
          {item.codigo ? (
            <span className="font-mono text-[11px] text-muted-foreground">{item.codigo}</span>
          ) : null}
        </div>
      </TableCell>
      <TableCell className="text-right tabular-nums">{formatMoney(item.custo)}</TableCell>
      <TableCell className="text-right tabular-nums text-muted-foreground">
        {formatPercent(item.pct)}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full"
              style={{ width: cssWidth(item.pct_acumulado), background: meta.cor }}
            />
          </div>
          <span className="w-12 text-right text-xs tabular-nums text-muted-foreground">
            {formatPercent(item.pct_acumulado, 0)}
          </span>
        </div>
      </TableCell>
    </TableRow>
  );
}

/** Pareto dependency-free: barras = custo individual, linha = % acumulado,
 * com guias em 80% e 95% (limiares A/B/C). */
function ParetoChart({ curva }: { curva: CurvaAbc }) {
  const W = 720;
  const H = 220;
  const padT = 14;
  const padB = 26;
  const padX = 8;
  const plotH = H - padT - padB;
  const plotW = W - padX * 2;

  const itens = curva.itens;
  const custos = itens.map((i) => Number(i.custo));
  const maxCusto = Math.max(...custos, 1);
  const step = plotW / itens.length;
  const gap = Math.min(step * 0.3, 8);
  const barW = Math.max(step - gap, 1);
  const yFor = (frac: number) => padT + plotH * (1 - frac); // frac 0..1 (eixo 0-100%)

  const linePts = itens.map((it, i) => {
    const cx = padX + i * step + step / 2;
    const cy = yFor(Number(it.pct_acumulado));
    return [cx, cy] as const;
  });
  const linePath = linePts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          Pareto — custo por item e curva acumulada
        </span>
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          {(["A", "B", "C"] as const).map((c) => (
            <span key={c} className="flex items-center gap-1">
              <span className="size-2 rounded-sm" style={{ background: CLASSE[c].cor }} />
              {c}
            </span>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Gráfico de Pareto da curva ABC">
        {/* guias 80% / 95% */}
        {[0.8, 0.95].map((t) => (
          <g key={t}>
            <line
              x1={padX}
              x2={W - padX}
              y1={yFor(t)}
              y2={yFor(t)}
              stroke="currentColor"
              strokeOpacity={0.25}
              strokeDasharray="4 4"
              vectorEffect="non-scaling-stroke"
            />
            <text x={W - padX} y={yFor(t) - 3} textAnchor="end" className="fill-muted-foreground text-[10px]">
              {t * 100}%
            </text>
          </g>
        ))}
        {/* barras */}
        {itens.map((it, i) => {
          const h = (Number(it.custo) / maxCusto) * plotH;
          const x = padX + i * step + (step - barW) / 2;
          const y = padT + plotH - h;
          return (
            <rect
              key={it.id}
              x={x}
              y={y}
              width={barW}
              height={Math.max(h, 0.5)}
              rx={1.5}
              fill={CLASSE[it.classe].cor}
              fillOpacity={0.85}
            >
              <title>
                {it.descricao} — {formatMoney(it.custo)} ({formatPercent(it.pct)})
              </title>
            </rect>
          );
        })}
        {/* linha acumulada */}
        <path d={linePath} fill="none" stroke="var(--color-primary)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
        {linePts.map((p, i) => (
          <circle key={i} cx={p[0]} cy={p[1]} r={2.5} fill="var(--color-primary)" />
        ))}
      </svg>
    </div>
  );
}
