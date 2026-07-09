"use client";

import * as React from "react";
import Link from "next/link";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type Column,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown, Trash2 } from "lucide-react";

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
import type { Ticket } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { TicketStatusBadge } from "./status";

interface ColMeta {
  headClassName?: string;
  cellClassName?: string;
}

function SortHeader({
  column,
  children,
}: {
  column: Column<Ticket, unknown>;
  children: React.ReactNode;
}) {
  const sorted = column.getIsSorted();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-2.5 h-7 text-muted-foreground"
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

function DeleteAction({
  ticket,
  onDelete,
  deleting,
}: {
  ticket: Ticket;
  onDelete: (ticket: Ticket) => void;
  deleting: boolean;
}) {
  return (
    <div className="flex justify-end">
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Excluir chamado"
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir chamado?</AlertDialogTitle>
            <AlertDialogDescription>
              O chamado{" "}
              <span className="font-medium text-foreground">{ticket.titulo}</span> e
              suas mensagens serão removidos.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => onDelete(ticket)}
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

interface TicketsTableProps {
  tickets: Ticket[];
  obraName: (id: string) => string;
  loading: boolean;
  deletingId: string | null;
  onDelete: (ticket: Ticket) => void;
}

export function TicketsTable({
  tickets,
  obraName,
  loading,
  deletingId,
  onDelete,
}: TicketsTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([]);

  const columns = React.useMemo<ColumnDef<Ticket>[]>(
    () => [
      {
        accessorKey: "titulo",
        header: ({ column }) => <SortHeader column={column}>Título</SortHeader>,
        cell: ({ row }) => (
          <Link
            href={`/tickets/${row.original.id}`}
            className="font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
          >
            {row.original.titulo}
          </Link>
        ),
      },
      {
        id: "obra",
        accessorFn: (row) => obraName(row.obra_id),
        header: ({ column }) => <SortHeader column={column}>Obra</SortHeader>,
        cell: ({ getValue }) => (
          <span className="text-muted-foreground">{getValue<string>()}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => <TicketStatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "created_at",
        header: ({ column }) => <SortHeader column={column}>Aberto em</SortHeader>,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {formatDate(row.original.created_at)}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <DeleteAction
            ticket={row.original}
            onDelete={onDelete}
            deleting={deletingId === row.original.id}
          />
        ),
        meta: { cellClassName: "w-0" },
      },
    ],
    [obraName, onDelete, deletingId],
  );

  const table = useReactTable({
    data: tickets,
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
                    : flexRender(header.column.columnDef.header, header.getContext())}
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
                Nenhum chamado encontrado.
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
