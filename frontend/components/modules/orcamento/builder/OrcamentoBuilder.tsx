"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FileText, Lock, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { OrcamentoStatus, VersaoResumo } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useObra } from "@/lib/hooks/use-obras";
import {
  useEapTree,
  useOrcamento,
  useUpdateOrcamentoStatus,
} from "@/lib/hooks/use-orcamentos";
import { ORCAMENTO_STATUS_OPTIONS, nextStatuses } from "../status";
import { BdiTab } from "./BdiTab";
import { EstruturaTab } from "./EstruturaTab";
import { ImportDialog } from "./ImportDialog";
import { PdfDialog } from "./PdfDialog";
import { PrecificacaoTab } from "./PrecificacaoTab";
import { ResumoTab } from "./ResumoTab";

type TabKey = "estrutura" | "precificacao" | "bdi" | "resumo";

const TABS: { key: TabKey; label: string }[] = [
  { key: "estrutura", label: "Estrutura" },
  { key: "precificacao", label: "Precificação" },
  { key: "bdi", label: "Curva ABC" },
  { key: "resumo", label: "Resumo" },
];

export function OrcamentoBuilder({ orcamentoId }: { orcamentoId: string }) {
  const router = useRouter();
  const [tab, setTab] = React.useState<TabKey>("estrutura");
  const [importOpen, setImportOpen] = React.useState(false);
  const [pdfOpen, setPdfOpen] = React.useState(false);

  const orcQuery = useOrcamento(orcamentoId);
  const orc = orcQuery.data;
  const versaoId = orc?.versao.id ?? "";
  const treeQuery = useEapTree(versaoId);
  const obraQuery = useObra(orc?.obra_id ?? "");
  const updateStatus = useUpdateOrcamentoStatus();

  const close = () => router.push("/orcamentos");

  const versao: VersaoResumo | undefined = treeQuery.data?.versao ?? (
    orc ? { ...orc.versao } : undefined
  );
  const locked = versao?.is_locked ?? false;
  const itens = treeQuery.data?.itens ?? [];

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      {/* Header */}
      <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-3.5">
        <div className="flex min-w-0 items-start gap-3">
          <Button variant="outline" size="icon-sm" onClick={close} aria-label="Fechar builder">
            <X />
          </Button>
          <div className="min-w-0">
            {orc ? (
              <>
                <div className="flex items-center gap-2">
                  <h1 className="truncate text-lg font-semibold tracking-tight">
                    {orc.titulo}
                  </h1>
                  <span className="flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
                    Rev. {orc.versao_atual}
                  </span>
                  {locked ? (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                      <Lock className="size-3" /> Aprovado — somente leitura
                    </span>
                  ) : null}
                </div>
                <p className="truncate text-sm text-muted-foreground">
                  {obraQuery.data
                    ? `${obraQuery.data.codigo} · ${obraQuery.data.nome}`
                    : "—"}
                </p>
              </>
            ) : (
              <div className="space-y-2">
                <Skeleton className="h-5 w-64" />
                <Skeleton className="h-4 w-40" />
              </div>
            )}
          </div>
        </div>

        {orc ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPdfOpen(true)}>
              <FileText /> Gerar PDF
            </Button>
            <span className="text-xs text-muted-foreground">Status</span>
            <Select
              value={orc.status}
              onValueChange={(v) =>
                updateStatus.mutate({ id: orc.id, status: v as OrcamentoStatus })
              }
              disabled={updateStatus.isPending}
            >
              <SelectTrigger size="sm" className="w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORCAMENTO_STATUS_OPTIONS.map((o) => {
                  const allowed = nextStatuses(orc.status).includes(o.value);
                  return (
                    <SelectItem key={o.value} value={o.value} disabled={!allowed}>
                      {o.label}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>
        ) : null}
      </header>

      {/* Tabs */}
      <nav className="flex items-center gap-1 border-b border-border px-5">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={cn(
              "relative px-4 py-3 text-sm font-medium transition-colors",
              tab === t.key
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
            {tab === t.key ? (
              <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-primary" />
            ) : null}
          </button>
        ))}
      </nav>

      {/* Conteúdo */}
      <main className="min-h-0 flex-1 overflow-hidden px-5 py-4">
        {treeQuery.isLoading || !versao ? (
          <div className="space-y-2 pt-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : tab === "estrutura" ? (
          <EstruturaTab
            versaoId={versaoId}
            itens={itens}
            locked={locked}
            onImport={() => setImportOpen(true)}
          />
        ) : tab === "precificacao" ? (
          <PrecificacaoTab versaoId={versaoId} versao={versao} itens={itens} locked={locked} />
        ) : tab === "bdi" ? (
          <BdiTab orcamentoId={orcamentoId} />
        ) : (
          <ResumoTab
            orcamentoId={orcamentoId}
            status={orc?.status ?? "rascunho"}
            versao={versao}
            itens={itens}
          />
        )}
      </main>

      {/* Barra de resumo */}
      <footer className="grid grid-cols-2 gap-4 border-t border-border px-5 py-3 sm:grid-cols-5">
        <SummaryStat label="Custo direto" value={formatMoney(versao?.custo_direto)} />
        <SummaryStat label="Markup global" value={formatPercent(versao?.markup_global)} />
        <SummaryStat label="Taxa adm." value={formatPercent(versao?.taxa_adm)} />
        <SummaryStat
          label="Preço de venda"
          value={formatMoney(versao?.preco_venda)}
          emphasis
        />
        <SummaryStat label="Margem" value={formatPercent(versao?.margem)} />
      </footer>

      {versaoId ? (
        <ImportDialog open={importOpen} onOpenChange={setImportOpen} versaoId={versaoId} />
      ) : null}
      {orc ? (
        <PdfDialog
          open={pdfOpen}
          onOpenChange={setPdfOpen}
          orcamentoId={orcamentoId}
          titulo={orc.titulo}
        />
      ) : null}
    </div>
  );
}

 
function SummaryStat({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div>
      <div className="text-[11px] tracking-wide text-muted-foreground/70 uppercase">
        {label}
      </div>
      <div
        className={cn(
          "tabular-nums",
          emphasis ? "text-lg font-semibold text-primary" : "text-sm font-medium",
        )}
      >
        {value}
      </div>
    </div>
  );
}
