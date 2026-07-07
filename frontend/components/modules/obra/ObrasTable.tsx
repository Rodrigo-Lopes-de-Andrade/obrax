"use client";

import * as React from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type Column,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowDown,
  ArrowUp,
  ChevronsUpDown,
  Pencil,
  Trash2,
} from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Obra } from "@/lib/api/types";
import { formatMoney } from "@/lib/decimal";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { StatusBadge } from "./status";

interface ColMeta {
  headClassName?: string;
  cellClassName?: string;
}

function SortHeader({
  column,
  children,
  className,
}: {
  column: Column<Obra, unknown>;
  children: React.ReactNode;
  className?: string;
}) {
  const sorted = column.getIsSorted();
  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("-ml-2.5 h-7 text-muted-foreground", className)}
      onClick={() => column.toggleSorting(sorted === "asc")}
    >
      {children}
      {sorted === "asc" ? (
        <ArrowUp />
      ) : sorted === "desc" ? (
        <ArrowDown />
      ) : (
        <ChevronsUpDown className="opacity-50" />
      )}
    </Button>
  );
}

function RowActions({
  obra,
  onEdit,
  onDelete,
  deleting,
}: {
  obra: Obra;
  onEdit: (obra: Obra) => void;
  onDelete: (obra: Obra) => void;
  deleting: boolean;
}) {
  return (
    <div className="flex justify-end gap-0.5">
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Editar obra"
        onClick={() => onEdit(obra)}
      >
        <Pencil />
      </Button>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Excluir obra"
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir obra?</AlertDialogTitle>
            <AlertDialogDescription>
              A obra <span className="font-medium text-foreground">{obra.codigo}</span>{" "}
              — {obra.nome} será removida da listagem.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => onDelete(obra)}
              className="bg-destructive/10 text-destructive hover:bg-destructive/20"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

interface ObrasTableProps {
  obras: Obra[];
  clienteName: (id: string) => string;
  loading: boolean;
  deletingId: string | null;
  onEdit: (obra: Obra) => void;
  onDelete: (obra: Obra) => void;
}

export function ObrasTable({
  obras,
  clienteName,
  loading,
  deletingId,
  onEdit,
  onDelete,
}: ObrasTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);

  const columns = React.useMemo<ColumnDef<Obra>[]>(
    () => [
      {
        accessorKey: "codigo",
        header: ({ column }) => <SortHeader column={column}>Código</SortHeader>,
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.codigo}</span>
        ),
      },
      {
        id: "cliente",
        accessorFn: (row) => clienteName(row.cliente_id),
        header: ({ column }) => <SortHeader column={column}>Cliente</SortHeader>,
        cell: ({ getValue }) => (
          <span className="font-medium">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "data_inicio",
        header: ({ column }) => <SortHeader column={column}>Início</SortHeader>,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {formatDate(row.original.data_inicio)}
          </span>
        ),
      },
      {
        accessorKey: "data_prevista_fim",
        header: ({ column }) => (
          <SortHeader column={column}>Previsão fim</SortHeader>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {formatDate(row.original.data_prevista_fim)}
          </span>
        ),
      },
      {
        accessorKey: "valor_contrato",
        header: ({ column }) => (
          <SortHeader column={column} className="w-full justify-end">
            Valor
          </SortHeader>
        ),
        cell: ({ row }) => (
          <div className="text-right tabular-nums">
            {row.original.valor_contrato
              ? formatMoney(row.original.valor_contrato)
              : "—"}
          </div>
        ),
        sortingFn: (a, b) =>
          Number(a.original.valor_contrato ?? -1) -
          Number(b.original.valor_contrato ?? -1),
        meta: { headClassName: "text-right", cellClassName: "text-right" },
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            obra={row.original}
            onEdit={onEdit}
            onDelete={onDelete}
            deleting={deletingId === row.original.id}
          />
        ),
        meta: { cellClassName: "w-0" },
      },
    ],
    [clienteName, onEdit, onDelete, deletingId],
  );

  const table = useReactTable({
    data: obras,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id} className="hover:bg-transparent">
              {hg.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={(header.column.columnDef.meta as ColMeta)?.headClassName}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <TableRow key={`skeleton-${i}`} className="hover:bg-transparent">
                {columns.map((_col, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-4 w-full max-w-28" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : table.getRowModel().rows.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={columns.length}
                className="h-24 text-center text-sm text-muted-foreground"
              >
                Nenhuma obra encontrada.
              </TableCell>
            </TableRow>
          ) : (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={(cell.column.columnDef.meta as ColMeta)?.cellClassName}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
