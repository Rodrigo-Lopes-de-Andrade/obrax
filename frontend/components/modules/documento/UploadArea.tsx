"use client";

import * as React from "react";
import { Check, Loader2, X } from "lucide-react";

import { FileDropzone } from "@/components/shared/FileDropzone";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUploadDocumentos } from "@/lib/hooks/use-documentos";
import type { DocumentoTipo } from "@/lib/api/types";
import { CATEGORIAS_SUGERIDAS, DOC_TIPO_OPTIONS } from "./doc-meta";

const SEM_CATEGORIA = "__sem__";

export function UploadArea({ obraId }: { obraId: string }) {
  const [tipo, setTipo] = React.useState<DocumentoTipo>("outro");
  const [categoria, setCategoria] = React.useState<string>(SEM_CATEGORIA);
  const { upload, uploads, dismiss } = useUploadDocumentos(obraId);

  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Tipo</span>
          <Select value={tipo} onValueChange={(v) => setTipo(v as DocumentoTipo)}>
            <SelectTrigger size="sm" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DOC_TIPO_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Categoria</span>
          <Select value={categoria} onValueChange={setCategoria}>
            <SelectTrigger size="sm" className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SEM_CATEGORIA}>Sem categoria</SelectItem>
              {CATEGORIAS_SUGERIDAS.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <FileDropzone
        onFiles={(files) =>
          upload(files, {
            tipo,
            categoria: categoria === SEM_CATEGORIA ? null : categoria,
          })
        }
      />

      {uploads.length > 0 ? (
        <ul className="space-y-1.5">
          {uploads.map((u) => (
            <li
              key={u.key}
              className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-1.5 text-sm"
            >
              {u.status === "uploading" ? (
                <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />
              ) : u.status === "done" ? (
                <Check className="size-4 shrink-0 text-emerald-400" />
              ) : (
                <X className="size-4 shrink-0 text-destructive" />
              )}
              <span className="min-w-0 flex-1 truncate">{u.name}</span>
              <span className="text-xs text-muted-foreground">
                {u.status === "uploading"
                  ? "Enviando…"
                  : u.status === "done"
                    ? "Enviado"
                    : "Falhou"}
              </span>
              {u.status === "error" ? (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Dispensar"
                  onClick={() => dismiss(u.key)}
                >
                  <X />
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
