"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { Building2, ChevronLeft, ChevronRight, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Obra, ObraStatus } from "@/lib/api/types";
import { useClientes } from "@/lib/hooks/use-clientes";
import { useDeleteObra, useObras } from "@/lib/hooks/use-obras";
import { cn } from "@/lib/utils";
// Code-split (F11.3): o drawer só é necessário ao criar/editar — sai do bundle inicial.
const ObraFormDrawer = dynamic(() => import("./ObraFormDrawer").then((m) => m.ObraFormDrawer));
import { ObrasTable } from "./ObrasTable";
import { OBRA_STATUS_OPTIONS } from "./status";

const PAGE_SIZE = 50;

export function ObrasView() {
  const [statusFilter, setStatusFilter] = React.useState<ObraStatus | "todos">(
    "todos",
  );
  // Pilha de cursores: cada entrada é o cursor da página seguinte já visitada.
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Obra | undefined>(undefined);

  const status = statusFilter === "todos" ? null : statusFilter;
  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;

  const { data, isLoading, isFetching, isError } = useObras({
    status,
    cursor,
    limit: PAGE_SIZE,
  });
  const { data: clientesPage } = useClientes();
  const deleteObra = useDeleteObra();

  const nameById = React.useMemo(
    () => new Map((clientesPage?.items ?? []).map((c) => [c.id, c.nome])),
    [clientesPage],
  );
  const clienteName = React.useCallback(
    (id: string) => nameById.get(id) ?? "—",
    [nameById],
  );

  const items = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const pageNumber = cursorStack.length + 1;

  function changeStatus(value: ObraStatus | "todos") {
    setStatusFilter(value);
    setCursorStack([]); // volta à primeira página ao trocar o filtro
  }

  function openCreate() {
    setEditing(undefined);
    setDrawerOpen(true);
  }

  function openEdit(obra: Obra) {
    setEditing(obra);
    setDrawerOpen(true);
  }

  const deletingId = deleteObra.isPending ? (deleteObra.variables ?? null) : null;
  const showInitialEmpty =
    !isLoading && items.length === 0 && status === null && !canPrev;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Obras</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie as obras vinculadas aos seus clientes.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus />
          Nova obra
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={changeStatus}>
          <SelectTrigger size="sm" className="w-44" aria-label="Filtrar por status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {OBRA_STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Não foi possível carregar as obras. Tente novamente.
        </div>
      ) : showInitialEmpty ? (
        <EmptyState
          icon={Building2}
          title="Nenhuma obra ainda"
          description="Crie a primeira obra para começar a acompanhar prazos, valores e status."
          actionLabel="Criar primeira obra"
          onAction={openCreate}
        />
      ) : (
        <>
          <div
            className={cn(
              "transition-opacity",
              isFetching && !isLoading ? "opacity-60" : "opacity-100",
            )}
          >
            <ObrasTable
              obras={items}
              clienteName={clienteName}
              loading={isLoading}
              deletingId={deletingId}
              onEdit={openEdit}
              onDelete={(obra) => deleteObra.mutate(obra.id)}
            />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {pageNumber}
              {items.length > 0 ? ` · ${items.length} obras` : ""}
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
                onClick={() =>
                  nextCursor && setCursorStack((s) => [...s, nextCursor])
                }
                disabled={!nextCursor || isFetching}
              >
                Próxima
                <ChevronRight />
              </Button>
            </div>
          </div>
        </>
      )}

      <ObraFormDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        obra={editing}
      />
    </div>
  );
}
