"use client";

import * as React from "react";
import { Building2, Download, FileClock, FileText, RefreshCw, Wallet } from "lucide-react";

import { KpiCard } from "@/components/shared/KpiCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  ObraStatus,
  OrcamentoStatus,
  RelatorioObrasAtivas,
  RelatorioOrcamentos,
} from "@/lib/api/types";
import { formatMoney, formatMoneyCompact } from "@/lib/format";
import {
  useObrasAtivasReport,
  useOrcamentosReport,
  useRefreshRelatorios,
} from "@/lib/hooks/use-relatorios";

const OBRA_LABEL: Record<ObraStatus, string> = {
  planejamento: "Planejamento",
  execucao: "Execução",
  pausada: "Pausada",
  concluida: "Concluída",
  cancelada: "Cancelada",
};
const OBRA_COR: Record<ObraStatus, string> = {
  planejamento: "#6366f1",
  execucao: "#059669",
  pausada: "#d97706",
  concluida: "#0ea5e9",
  cancelada: "#dc2626",
};
const ORC_LABEL: Record<OrcamentoStatus, string> = {
  rascunho: "Rascunho",
  em_revisao: "Em revisão",
  aguardando_aprovacao: "Aguardando aprovação",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};
const ORC_COR: Record<OrcamentoStatus, string> = {
  rascunho: "#8b93a4",
  em_revisao: "#6366f1",
  aguardando_aprovacao: "#d97706",
  aprovado: "#059669",
  rejeitado: "#dc2626",
};

/** CSV pt-BR (separador `;`, decimal com vírgula) + BOM p/ o Excel abrir em UTF-8. */
function downloadCsv(filename: string, headers: string[], rows: string[][]): void {
  const escape = (c: string) => `"${c.replace(/"/g, '""')}"`;
  const body = [headers, ...rows].map((r) => r.map(escape).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿" + body], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const csvMoney = (v: string) => Number(v).toFixed(2).replace(".", ",");

export function RelatoriosView() {
  const [from, setFrom] = React.useState("");
  const [to, setTo] = React.useState("");
  const params = React.useMemo(
    () => ({ from: from || null, to: to || null }),
    [from, to],
  );

  const obrasQuery = useObrasAtivasReport(params);
  const orcQuery = useOrcamentosReport(params);
  const refresh = useRefreshRelatorios();

  const loading = obrasQuery.isLoading || orcQuery.isLoading;
  const fetching = obrasQuery.isFetching || orcQuery.isFetching;
  const obras = obrasQuery.data;
  const orc = orcQuery.data;

  const updatedAt = Math.max(obrasQuery.dataUpdatedAt, orcQuery.dataUpdatedAt);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[27px] font-extrabold tracking-tight">Relatórios</h1>
          <p className="text-sm text-muted-foreground">
            Visão consolidada de obras e orçamentos por status
            {updatedAt > 0 ? (
              <>
                {" · "}
                <span title="Os relatórios são cacheados por 5 min no servidor">
                  atualizado às{" "}
                  {new Date(updatedAt).toLocaleTimeString("pt-BR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <DateField label="De" value={from} max={to || undefined} onChange={setFrom} />
          <DateField label="Até" value={to} min={from || undefined} onChange={setTo} />
          {(from || to) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFrom("");
                setTo("");
              }}
            >
              Limpar
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={refresh} disabled={fetching}>
            <RefreshCw className={fetching ? "animate-spin" : ""} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[132px] rounded-[10px]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard
            label="Obras Ativas"
            value={String(obras?.ativas ?? 0)}
            icon={Building2}
            iconClassName="text-secondary"
            iconBgClassName="bg-secondary/14"
            helperText={`de ${obras?.total ?? 0} no período`}
          />
          <KpiCard
            label="Valor em Obras Ativas"
            value={formatMoneyCompact(obras?.valor_ativas ?? "0")}
            icon={Wallet}
            iconClassName="text-success"
            iconBgClassName="bg-success/14"
            helperText="somatório dos contratos"
          />
          <KpiCard
            label="Total Orçado"
            value={formatMoneyCompact(orc?.preco_venda_total ?? "0")}
            icon={FileText}
            iconClassName="text-secondary"
            iconBgClassName="bg-secondary/14"
            helperText={`${orc?.total ?? 0} orçamentos`}
          />
          <KpiCard
            label="Orçamentos Pendentes"
            value={String(orc?.pendentes ?? 0)}
            icon={FileClock}
            iconClassName="text-primary"
            iconBgClassName="bg-primary/16"
            warn={(orc?.pendentes ?? 0) > 0}
            helperText="aguardando aprovação"
          />
        </div>
      )}

      {/* Tabelas */}
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ObrasTable data={obras} loading={loading} />
        <OrcamentosTable data={orc} loading={loading} />
      </div>
    </div>
  );
}

function DateField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: string;
  min?: string;
  max?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium tracking-wide text-muted-foreground/70 uppercase">
        {label}
      </span>
      <Input
        type="date"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-40"
      />
    </label>
  );
}

function ReportCard({
  title,
  onExport,
  children,
}: {
  title: string;
  onExport: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        <Button variant="ghost" size="sm" onClick={onExport}>
          <Download /> CSV
        </Button>
      </div>
      {children}
    </div>
  );
}

function StatusDot({ cor }: { cor: string }) {
  return <span className="inline-block size-2 rounded-full" style={{ background: cor }} />;
}

function ObrasTable({ data, loading }: { data?: RelatorioObrasAtivas; loading: boolean }) {
  const exportCsv = () =>
    downloadCsv(
      "relatorio-obras.csv",
      ["Status", "Quantidade", "Valor (R$)"],
      (data?.por_status ?? []).map((l) => [OBRA_LABEL[l.status], String(l.count), csvMoney(l.valor)]),
    );

  return (
    <ReportCard title="Obras por status" onExport={exportCsv}>
      {loading || !data ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Qtd.</TableHead>
              <TableHead className="text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.por_status.map((l) => (
              <TableRow key={l.status}>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <StatusDot cor={OBRA_COR[l.status]} />
                    {OBRA_LABEL[l.status]}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums">{l.count}</TableCell>
                <TableCell className="text-right tabular-nums">{formatMoney(l.valor)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell className="font-semibold">Ativas</TableCell>
              <TableCell className="text-right font-semibold tabular-nums">{data.ativas}</TableCell>
              <TableCell className="text-right font-semibold tabular-nums">
                {formatMoney(data.valor_ativas)}
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )}
    </ReportCard>
  );
}

function OrcamentosTable({ data, loading }: { data?: RelatorioOrcamentos; loading: boolean }) {
  const exportCsv = () =>
    downloadCsv(
      "relatorio-orcamentos.csv",
      ["Status", "Quantidade", "Preço de venda (R$)"],
      (data?.por_status ?? []).map((l) => [
        ORC_LABEL[l.status],
        String(l.count),
        csvMoney(l.preco_venda),
      ]),
    );

  return (
    <ReportCard title="Orçamentos por status" onExport={exportCsv}>
      {loading || !data ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Qtd.</TableHead>
              <TableHead className="text-right">Preço de venda</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.por_status.map((l) => (
              <TableRow key={l.status}>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <StatusDot cor={ORC_COR[l.status]} />
                    {ORC_LABEL[l.status]}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums">{l.count}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(l.preco_venda)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell className="font-semibold">Total</TableCell>
              <TableCell className="text-right font-semibold tabular-nums">{data.total}</TableCell>
              <TableCell className="text-right font-semibold tabular-nums">
                {formatMoney(data.preco_venda_total)}
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )}
    </ReportCard>
  );
}
