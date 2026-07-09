"use client";

import { Skeleton } from "@/components/ui/skeleton";
import type { Documento } from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";
import { DocDeleteButton } from "./DocDeleteButton";
import { DocTipoBadge, DocTipoIcon } from "./doc-meta";
import { VisibilidadeToggle } from "./VisibilidadeToggle";

interface DocumentosGalleryProps {
  docs: Documento[];
  loading: boolean;
  deletingId: string | null;
  onDelete: (doc: Documento) => void;
  onToggleVisibilidade: (doc: Documento) => void;
}

const GRID = "grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3";

export function DocumentosGallery({
  docs,
  loading,
  deletingId,
  onDelete,
  onToggleVisibilidade,
}: DocumentosGalleryProps) {
  if (loading) {
    return (
      <div className={GRID}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="rounded-xl border border-border py-16 text-center text-sm text-muted-foreground">
        Nenhum documento encontrado.
      </div>
    );
  }

  return (
    <div className={GRID}>
      {docs.map((doc) => (
        <div
          key={doc.id}
          className="group flex flex-col gap-3 rounded-xl border border-border p-4 transition-colors hover:border-muted-foreground/30"
        >
          <div className="flex items-start gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
              <DocTipoIcon tipo={doc.tipo} className="size-4.5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" title={doc.nome}>
                {doc.nome}
              </p>
              <p className="text-xs text-muted-foreground tabular-nums">
                {formatBytes(doc.size_bytes)} · {formatDate(doc.created_at)}
              </p>
            </div>
            <DocDeleteButton
              doc={doc}
              onDelete={onDelete}
              deleting={deletingId === doc.id}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <DocTipoBadge tipo={doc.tipo} />
            {doc.categoria ? (
              <span className="text-xs text-muted-foreground">{doc.categoria}</span>
            ) : null}
            <span className="ml-auto">
              <VisibilidadeToggle
                visivel={doc.visivel_cliente}
                onToggle={() => onToggleVisibilidade(doc)}
              />
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
