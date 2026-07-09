"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Documento } from "@/lib/api/types";
import { formatBytes, formatDate } from "@/lib/format";
import { DocDeleteButton } from "./DocDeleteButton";
import { DocTipoBadge, DocTipoIcon } from "./doc-meta";
import { VisibilidadeToggle } from "./VisibilidadeToggle";

interface DocumentosTableProps {
  docs: Documento[];
  loading: boolean;
  deletingId: string | null;
  onDelete: (doc: Documento) => void;
  selected: Set<string>;
  onToggleSelect: (id: string) => void;
  onToggleAll: () => void;
  onToggleVisibilidade: (doc: Documento) => void;
}

export function DocumentosTable({
  docs,
  loading,
  deletingId,
  onDelete,
  selected,
  onToggleSelect,
  onToggleAll,
  onToggleVisibilidade,
}: DocumentosTableProps) {
  const allSelected = docs.length > 0 && docs.every((d) => selected.has(d.id));
  const someSelected = docs.some((d) => selected.has(d.id));

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-0">
              <Checkbox
                checked={allSelected ? true : someSelected ? "indeterminate" : false}
                onCheckedChange={onToggleAll}
                aria-label="Selecionar todos"
                disabled={docs.length === 0}
              />
            </TableHead>
            <TableHead>Documento</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Categoria</TableHead>
            <TableHead>Visibilidade</TableHead>
            <TableHead>Enviado em</TableHead>
            <TableHead className="w-0" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <TableRow key={`sk-${i}`} className="hover:bg-transparent">
                {Array.from({ length: 7 }).map((_c, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-4 w-full max-w-32" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : docs.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={7}
                className="h-24 text-center text-sm text-muted-foreground"
              >
                Nenhum documento encontrado.
              </TableCell>
            </TableRow>
          ) : (
            docs.map((doc) => (
              <TableRow key={doc.id} data-state={selected.has(doc.id) ? "selected" : undefined}>
                <TableCell className="w-0">
                  <Checkbox
                    checked={selected.has(doc.id)}
                    onCheckedChange={() => onToggleSelect(doc.id)}
                    aria-label={`Selecionar ${doc.nome}`}
                  />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2.5">
                    <DocTipoIcon tipo={doc.tipo} className="size-4.5 shrink-0" />
                    <div className="min-w-0">
                      <p className="truncate font-medium">{doc.nome}</p>
                      <p className="text-xs text-muted-foreground tabular-nums">
                        {formatBytes(doc.size_bytes)}
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <DocTipoBadge tipo={doc.tipo} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {doc.categoria ?? "—"}
                </TableCell>
                <TableCell>
                  <VisibilidadeToggle
                    visivel={doc.visivel_cliente}
                    onToggle={() => onToggleVisibilidade(doc)}
                  />
                </TableCell>
                <TableCell className="text-muted-foreground tabular-nums">
                  {formatDate(doc.created_at)}
                </TableCell>
                <TableCell className="w-0">
                  <div className="flex justify-end">
                    <DocDeleteButton
                      doc={doc}
                      onDelete={onDelete}
                      deleting={deletingId === doc.id}
                    />
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
