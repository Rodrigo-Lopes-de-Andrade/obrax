"use client";

import * as React from "react";
import { AlertTriangle, Download, FileSpreadsheet, Loader2, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TEMPLATE_URL } from "@/lib/api/orcamentos";
import type { ImportErro } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { importErros, useImportPlanilha } from "@/lib/hooks/use-orcamentos";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  versaoId: string;
}

export function ImportDialog({ open, onOpenChange, versaoId }: Props) {
  const importar = useImportPlanilha(versaoId);
  const [file, setFile] = React.useState<File | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [erros, setErros] = React.useState<ImportErro[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setFile(null);
      setErros([]);
    }
  }, [open]);

  if (!open) return null;

  const pick = (f: File | null | undefined) => {
    if (f) {
      setFile(f);
      setErros([]);
    }
  };

  const submit = () => {
    if (!file) return;
    setErros([]);
    importar.mutate(file, {
      onSuccess: () => onOpenChange(false),
      onError: (e) => setErros(importErros(e)),
    });
  };

  const downloadTemplate = async () => {
    const res = await fetch(TEMPLATE_URL, { credentials: "include" });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "modelo_orcamento.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/50 p-4 pt-[10vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="flex max-h-[80vh] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-border bg-popover shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div>
            <h2 className="text-base font-semibold">Importar planilha</h2>
            <p className="text-xs text-muted-foreground">
              XLSX no modelo (Fase / Serviço / Insumo) — até 5.000 linhas.
            </p>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={() => onOpenChange(false)} aria-label="Fechar">
            <X />
          </Button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <button
            type="button"
            onClick={downloadTemplate}
            className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-sm hover:bg-white/5"
          >
            <Download className="size-4 text-muted-foreground" />
            Baixar modelo XLSX
          </button>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              pick(e.dataTransfer.files?.[0]);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors",
              dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
            )}
          >
            {file ? (
              <>
                <FileSpreadsheet className="size-8 text-emerald-400" />
                <span className="text-sm font-medium">{file.name}</span>
                <span className="text-xs text-muted-foreground">Clique para trocar o arquivo</span>
              </>
            ) : (
              <>
                <UploadCloud className="size-8 text-muted-foreground/50" />
                <span className="text-sm">Arraste o arquivo aqui ou clique para selecionar</span>
                <span className="text-xs text-muted-foreground">.xlsx até 30 MB</span>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              onChange={(e) => pick(e.target.files?.[0])}
            />
          </div>

          {erros.length > 0 ? (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5">
              <div className="flex items-center gap-2 border-b border-destructive/20 px-3 py-2 text-sm font-medium text-destructive">
                <AlertTriangle className="size-4" />
                {erros.length} {erros.length === 1 ? "erro encontrado" : "erros encontrados"}
              </div>
              <div className="max-h-48 overflow-y-auto divide-y divide-destructive/10">
                {erros.map((e, i) => (
                  <div key={i} className="flex items-baseline gap-2 px-3 py-1.5 text-sm">
                    <span className="w-14 flex-shrink-0 font-medium tabular-nums text-destructive">
                      Linha {e.linha}
                    </span>
                    <span className="w-24 flex-shrink-0 text-xs text-muted-foreground">
                      {e.campo}
                    </span>
                    <span className="min-w-0 flex-1">{e.mensagem}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={importar.isPending}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={!file || importar.isPending}>
            {importar.isPending ? <Loader2 className="animate-spin" /> : <UploadCloud />}
            Importar
          </Button>
        </div>
      </div>
    </div>
  );
}
