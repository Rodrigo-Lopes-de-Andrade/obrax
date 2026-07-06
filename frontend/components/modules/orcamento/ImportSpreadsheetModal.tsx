"use client";

import {
  X,
  FileSpreadsheet,
  Download,
  FileCheck2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { useUiStore } from "@/state/ui";
import { impErrRows } from "@/lib/mock/dashboard-obra";

export function ImportSpreadsheetModal() {
  const open = useUiStore((s) => s.importModalOpen);
  const importState = useUiStore((s) => s.importState);
  const importDrag = useUiStore((s) => s.importDrag);
  const closeImportModal = useUiStore((s) => s.closeImportModal);
  const resetImport = useUiStore((s) => s.resetImport);
  const setImportDrag = useUiStore((s) => s.setImportDrag);
  const startImportValidation = useUiStore((s) => s.startImportValidation);
  const confirmImport = useUiStore((s) => s.confirmImport);

  if (!open) return null;

  const isValidating = importState === "processing" || importState === "errors" || importState === "clean";

  return (
    <div
      onClick={closeImportModal}
      className="fixed inset-0 z-60 flex items-center justify-center bg-black/70 p-8 backdrop-blur-[2px]"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-160 overflow-hidden rounded-2xl bg-card shadow-[0_0_40px_rgba(0,0,0,0.5),0_0_0_1px_rgba(255,255,255,0.06)]"
      >
        <div className="flex items-center justify-between border-b border-white/6 px-6 py-5">
          <h2 className="text-[17px] font-extrabold">Importar planilha de orçamento</h2>
          <button
            type="button"
            onClick={closeImportModal}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-[9px] border border-white/7 bg-white/5 text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {importState === "upload" && (
          <div className="p-6">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                if (!importDrag) setImportDrag(true);
              }}
              onDragLeave={() => setImportDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setImportDrag(false);
                startImportValidation();
              }}
              onClick={startImportValidation}
              className="cursor-pointer rounded-xl border-2 border-dashed bg-[#2d3142] px-6 py-11 text-center transition-colors"
              style={{ borderColor: importDrag ? "var(--color-secondary)" : "#3a3f52" }}
            >
              <FileSpreadsheet className="mx-auto h-12 w-12 text-secondary" />
              <div className="mt-2.5 text-base font-semibold">Arraste sua planilha aqui</div>
              <div className="mt-0.75 text-[13px] text-muted-foreground">ou clique para selecionar</div>
              <button
                type="button"
                className="mt-4 rounded-lg bg-primary px-4.5 py-2.25 text-[13px] font-bold text-primary-foreground shadow-[0_4px_14px_rgba(255,107,107,0.28)]"
              >
                Selecionar arquivo
              </button>
              <div className="mt-3 text-xs text-[#5b6072]">Aceita: .xlsx, .xls · Máx. 30 MB</div>
            </div>
            <div className="mt-4.5 flex items-center gap-2.25 text-[13px]">
              <Download className="h-4 w-4 text-primary" />
              <span className="font-semibold text-primary">Baixar template Obrax.xlsx</span>
              <span className="text-muted-foreground">— use o template para garantir importação sem erros</span>
            </div>
            <div className="mt-3.5 rounded-lg bg-white/3 px-3.25 py-2.75 font-mono text-xs text-muted-foreground">
              Estrutura esperada: Fase | Serviço | Insumo | Un | Qtd | Preço unit.
            </div>
          </div>
        )}

        {isValidating && (
          <>
            <div className="p-6">
              <div className="mb-3.5 flex items-center gap-2.75">
                <FileCheck2 className="h-5.5 w-5.5 text-success" />
                <div>
                  <div className="text-sm font-semibold">orcamento_vila_aurora.xlsx</div>
                  <div className="text-xs text-muted-foreground">847 KB · 312 linhas detectadas</div>
                </div>
              </div>

              {importState === "processing" && (
                <div>
                  <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-white/8">
                    <div className="h-full w-3/4 rounded-full bg-secondary" />
                  </div>
                  <div className="text-[13px] text-muted-foreground">Validando estrutura…</div>
                </div>
              )}

              {importState === "errors" && (
                <div>
                  <div className="mb-1.5 flex items-center gap-2.25">
                    <AlertTriangle className="h-4.5 w-4.5 text-[#fcc419]" />
                    <span className="text-sm font-bold text-[#fcc419]">3 erros encontrados</span>
                  </div>
                  <p className="mb-3.5 text-[12.5px] text-muted-foreground">
                    Corrija os erros abaixo antes de importar
                  </p>
                  <div className="overflow-hidden rounded-[9px] border border-white/6">
                    <div className="grid grid-cols-[70px_130px_1fr] border-b border-white/6 bg-[#2d3142] text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
                      <div className="px-3 py-2.25">Linha</div>
                      <div className="px-2 py-2.25">Campo</div>
                      <div className="px-2 py-2.25">Problema</div>
                    </div>
                    {impErrRows.map((row) => (
                      <div
                        key={row.linha}
                        className="grid grid-cols-[70px_130px_1fr] border-b border-white/4 last:border-b-0"
                      >
                        <div className="px-3 py-2.5 font-mono text-[12.5px] text-primary">{row.linha}</div>
                        <div className="px-2 py-2.5 text-[12.5px] text-subtle-foreground">{row.campo}</div>
                        <div className="px-2 py-2.5 text-[12.5px] text-muted-foreground">{row.problema}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {importState === "clean" && (
                <div className="rounded-[10px] border border-success/20 bg-success/8 p-4">
                  <div className="mb-2 flex items-center gap-2.25">
                    <CheckCircle2 className="h-4.5 w-4.5 text-success" />
                    <span className="text-sm font-bold text-success">312 linhas prontas</span>
                  </div>
                  <div className="text-[13px] text-subtle-foreground">Preview: 4 Fases · 18 Serviços · 290 Insumos</div>
                  <div className="mt-0.75 text-[13px] text-subtle-foreground">
                    Custo direto estimado: <b className="font-mono">R$ 2,84 mi</b>
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2.5 border-t border-white/6 bg-[#1b1e27] px-6 py-4">
              <button
                type="button"
                onClick={resetImport}
                className="rounded-lg border border-white/12 px-4 py-2.25 text-[13px] font-semibold text-subtle-foreground"
              >
                Escolher outro arquivo
              </button>
              <button
                type="button"
                onClick={confirmImport}
                disabled={importState !== "clean"}
                className={`rounded-lg px-5 py-2.25 text-[13px] font-bold shadow-[0_4px_14px_rgba(255,107,107,0.22)] ${
                  importState === "clean"
                    ? "cursor-pointer bg-primary text-primary-foreground"
                    : "cursor-not-allowed bg-[#3a3f52] text-[#5b6072] opacity-60"
                }`}
              >
                Importar
              </button>
            </div>
          </>
        )}

        {importState === "done" && (
          <div className="px-6 py-12 text-center">
            <CheckCircle2 className="mx-auto h-16 w-16 text-success" />
            <div className="mt-4 text-xl font-extrabold">Importação concluída!</div>
            <div className="mt-1.5 text-[13.5px] text-muted-foreground">
              312 linhas importadas · 4 fases criadas
            </div>
            <button
              type="button"
              onClick={closeImportModal}
              className="mt-5.5 rounded-lg bg-primary px-5.5 py-2.75 text-[13.5px] font-bold text-primary-foreground shadow-[0_4px_14px_rgba(255,107,107,0.28)]"
            >
              Ver orçamento
            </button>
            <div className="mt-3.5">
              <button type="button" onClick={resetImport} className="text-[13px] font-semibold text-primary">
                Importar outro arquivo
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
