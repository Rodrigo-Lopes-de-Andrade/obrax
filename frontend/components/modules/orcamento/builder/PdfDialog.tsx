"use client";

import * as React from "react";
import { Download, FileText, Loader2, RefreshCw, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { useGerarPdf, usePdfStatus } from "@/lib/hooks/use-orcamentos";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orcamentoId: string;
  titulo: string;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function PdfDialog({ open, onOpenChange, orcamentoId, titulo }: Props) {
  const status = usePdfStatus(orcamentoId, open);
  const gerar = useGerarPdf(orcamentoId);

  // 404 = ainda não gerado (estado esperado, não erro de verdade).
  const naoGerado = status.error instanceof ApiError && status.error.status === 404;
  const erroStatus = status.isError && !naoGerado;
  const pdf = status.data;

  // Artefato HTML (dev/mock) → busca e injeta via srcDoc (o service worker do
  // MSW não intercepta navegação de iframe). PDF real (prod) → iframe src, que
  // aciona o visualizador nativo do browser.
  const isHtml = pdf?.content_type.includes("html") ?? false;
  const [srcDoc, setSrcDoc] = React.useState<string | null>(null);
  React.useEffect(() => {
    setSrcDoc(null);
    if (!pdf || !isHtml) return;
    let cancelled = false;
    fetch(pdf.download_url, { credentials: "include" })
      .then((r) => r.text())
      .then((html) => !cancelled && setSrcDoc(html))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [pdf, isHtml]);

  const baixar = () => {
    if (!pdf) return;
    if (isHtml && srcDoc != null) {
      // Artefato HTML: baixa o conteúdo já carregado (o link do mock é servido
      // pelo MSW, que não intercepta navegação/download direto).
      const url = URL.createObjectURL(new Blob([srcDoc], { type: "text/html" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${titulo || "orcamento"}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      window.open(pdf.download_url, "_blank", "noopener");
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-stretch justify-center bg-black/50 p-0 sm:items-start sm:p-4 sm:pt-[6vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="flex h-full w-full flex-col overflow-hidden border-border bg-popover shadow-2xl sm:h-[86vh] sm:max-w-4xl sm:rounded-xl sm:border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <FileText className="size-5 flex-shrink-0 text-primary" />
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold">PDF do orçamento</h2>
              <p className="truncate text-xs text-muted-foreground">{titulo}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {pdf ? (
              <>
                <Button variant="outline" size="sm" onClick={baixar}>
                  <Download /> Baixar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => gerar.mutate()}
                  disabled={gerar.isPending}
                >
                  {gerar.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                  Regerar
                </Button>
              </>
            ) : null}
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onOpenChange(false)}
              aria-label="Fechar"
            >
              <X />
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 bg-muted/30">
          {status.isLoading ? (
            <div className="p-5">
              <Skeleton className="h-full min-h-[50vh] w-full" />
            </div>
          ) : erroStatus ? (
            <CenteredState
              title="Não foi possível carregar o PDF"
              description="Ocorreu um erro ao consultar o status. Tente gerar novamente."
              action={
                <Button onClick={() => gerar.mutate()} disabled={gerar.isPending}>
                  {gerar.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                  Tentar novamente
                </Button>
              }
            />
          ) : gerar.isPending && !pdf ? (
            <CenteredState
              icon={<Loader2 className="size-8 animate-spin text-primary" />}
              title="Gerando PDF…"
              description="Montando o documento timbrado com a EAP, precificação e curva ABC."
            />
          ) : pdf ? (
            <div className="flex h-full flex-col">
              {isHtml && srcDoc === null ? (
                <div className="flex flex-1 items-center justify-center">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <iframe
                  title="Pré-visualização do PDF"
                  {...(isHtml ? { srcDoc: srcDoc ?? "" } : { src: pdf.download_url })}
                  className="min-h-0 w-full flex-1 border-0 bg-white"
                />
              )}
              <div className="border-t border-border px-5 py-2 text-center text-xs text-muted-foreground">
                Gerado em {formatDateTime(pdf.gerado_em)} · link de download válido por 1h
              </div>
            </div>
          ) : (
            <CenteredState
              icon={<FileText className="size-8 text-muted-foreground/50" />}
              title="Nenhum PDF gerado ainda"
              description="Gere o PDF timbrado do orçamento para visualizar e baixar."
              action={
                <Button onClick={() => gerar.mutate()} disabled={gerar.isPending}>
                  {gerar.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
                  Gerar PDF
                </Button>
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}

function CenteredState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      {icon}
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}
