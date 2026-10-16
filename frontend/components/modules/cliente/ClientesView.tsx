"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { ChevronLeft, ChevronRight, Pencil, Plus, Search, Trash2, Users } from "lucide-react";

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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Cliente } from "@/lib/api/types";
import { useClientesPage, useDeleteCliente } from "@/lib/hooks/use-clientes";
import { cn } from "@/lib/utils";
import { formatDocumento } from "./documento";
// Code-split: o drawer só é necessário ao criar/editar.
const ClienteFormDrawer = dynamic(() =>
  import("./ClienteFormDrawer").then((m) => m.ClienteFormDrawer),
);

const PAGE_SIZE = 50;

export function ClientesView() {
  const [searchInput, setSearchInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Cliente | undefined>(undefined);

  // Busca vinda da Topbar (`/clientes?q=`). Lido no efeito (e não via
  // useSearchParams) para a rota continuar estática sem Suspense boundary.
  React.useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) setSearchInput(q);
  }, []);

  React.useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setCursorStack([]);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;
  const { data, isLoading, isFetching, isError } = useClientesPage({
    search: search || null,
    cursor,
    limit: PAGE_SIZE,
  });
  const deleteCliente = useDeleteCliente();

  const items = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const deletingId = deleteCliente.isPending ? (deleteCliente.variables ?? null) : null;
  const showInitialEmpty = !isLoading && items.length === 0 && !search && !canPrev;

  function openCreate() {
    setEditing(undefined);
    setDrawerOpen(true);
  }

  function openEdit(cliente: Cliente) {
    setEditing(cliente);
    setDrawerOpen(true);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Clientes</h1>
          <p className="text-sm text-muted-foreground">
            Pessoas e empresas donas das obras.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus />
          Novo cliente
        </Button>
      </div>

      {!showInitialEmpty && (
        <div className="relative max-w-sm">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar por nome ou documento"
            aria-label="Buscar clientes"
            className="pl-9"
          />
        </div>
      )}

      {isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Não foi possível carregar os clientes. Tente novamente.
        </div>
      ) : showInitialEmpty ? (
        <EmptyState
          icon={Users}
          title="Nenhum cliente ainda"
          description="Cadastre o primeiro cliente para poder criar obras vinculadas a ele."
          actionLabel="Cadastrar primeiro cliente"
          onAction={openCreate}
        />
      ) : (
        <>
          <div
            className={cn(
              "rounded-xl border border-border transition-opacity",
              isFetching && !isLoading ? "opacity-60" : "opacity-100",
            )}
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Documento</TableHead>
                  <TableHead className="hidden md:table-cell">Telefone</TableHead>
                  <TableHead className="hidden md:table-cell">E-mail</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading
                  ? Array.from({ length: 4 }, (_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={5}>
                          <Skeleton className="h-5 w-full" />
                        </TableCell>
                      </TableRow>
                    ))
                  : items.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="font-medium">{c.nome}</TableCell>
                        <TableCell className="tabular-nums text-muted-foreground">
                          <span className="mr-1.5 rounded bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-foreground">
                            {c.tipo_pessoa}
                          </span>
                          {formatDocumento(c.documento)}
                        </TableCell>
                        <TableCell className="hidden text-muted-foreground md:table-cell">
                          {c.telefone ?? "—"}
                        </TableCell>
                        <TableCell className="hidden text-muted-foreground md:table-cell">
                          {c.email ?? "—"}
                        </TableCell>
                        <TableCell>
                          <RowActions
                            cliente={c}
                            onEdit={openEdit}
                            onDelete={(x) => deleteCliente.mutate(x.id)}
                            deleting={deletingId === c.id}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                {!isLoading && items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                      Nenhum cliente encontrado para &ldquo;{search}&rdquo;.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {cursorStack.length + 1}
              {items.length > 0 ? ` · ${items.length} clientes` : ""}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCursorStack((s) => s.slice(0, -1))}
                disabled={!canPrev || isFetching}
              >
                <ChevronLeft />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => nextCursor && setCursorStack((s) => [...s, nextCursor])}
                disabled={!nextCursor || isFetching}
              >
                Próxima
                <ChevronRight />
              </Button>
            </div>
          </div>
        </>
      )}

      <ClienteFormDrawer open={drawerOpen} onOpenChange={setDrawerOpen} cliente={editing} />
    </div>
  );
}

function RowActions({
  cliente,
  onEdit,
  onDelete,
  deleting,
}: {
  cliente: Cliente;
  onEdit: (c: Cliente) => void;
  onDelete: (c: Cliente) => void;
  deleting: boolean;
}) {
  return (
    <div className="flex justify-end gap-0.5">
      <Button variant="ghost" size="icon-sm" aria-label="Editar cliente" onClick={() => onEdit(cliente)}>
        <Pencil />
      </Button>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Excluir cliente"
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir cliente?</AlertDialogTitle>
            <AlertDialogDescription>
              <span className="font-medium text-foreground">{cliente.nome}</span> sai da listagem e
              não aparece mais para novas obras. As obras já vinculadas continuam como estão.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => onDelete(cliente)}
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
