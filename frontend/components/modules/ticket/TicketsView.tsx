"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, MessageSquarePlus, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Ticket, TicketStatus } from "@/lib/api/types";
import { useObras } from "@/lib/hooks/use-obras";
import { useDeleteTicket, useTickets } from "@/lib/hooks/use-tickets";
import { cn } from "@/lib/utils";
import { CreateTicketDrawer } from "./CreateTicketDrawer";
import { TicketsTable } from "./TicketsTable";
import { TICKET_STATUS_OPTIONS } from "./status";

const PAGE_SIZE = 30;

export function TicketsView() {
  const [statusFilter, setStatusFilter] = React.useState<TicketStatus | "todos">("todos");
  const [searchInput, setSearchInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  // Debounce da busca (evita refetch a cada tecla) + volta à 1ª página.
  React.useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setCursorStack([]);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const status = statusFilter === "todos" ? null : statusFilter;
  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;

  const { data, isLoading, isFetching, isError } = useTickets({
    status,
    search: search || null,
    cursor,
    limit: PAGE_SIZE,
  });
  const { data: obrasPage } = useObras({ limit: 100 });
  const deleteTicket = useDeleteTicket();

  const nameById = React.useMemo(
    () => new Map((obrasPage?.items ?? []).map((o) => [o.id, `${o.codigo} · ${o.nome}`])),
    [obrasPage],
  );
  const obraName = React.useCallback(
    (id: string) => nameById.get(id) ?? "—",
    [nameById],
  );

  const items = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const pageNumber = cursorStack.length + 1;

  function changeStatus(value: TicketStatus | "todos") {
    setStatusFilter(value);
    setCursorStack([]);
  }

  const deletingId = deleteTicket.isPending ? (deleteTicket.variables ?? null) : null;
  const noFilters = status === null && search === "";
  const showInitialEmpty = !isLoading && items.length === 0 && noFilters && !canPrev;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Chamados</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe e responda os chamados abertos nas obras.
          </p>
        </div>
        <Button onClick={() => setDrawerOpen(true)}>
          <Plus />
          Novo chamado
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={changeStatus}>
          <SelectTrigger size="sm" className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {TICKET_STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar por título…"
            className="pl-8"
          />
        </div>
      </div>

      {isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Não foi possível carregar os chamados. Tente novamente.
        </div>
      ) : showInitialEmpty ? (
        <EmptyState
          icon={MessageSquarePlus}
          title="Nenhum chamado ainda"
          description="Abra o primeiro chamado para registrar ocorrências e conversar com a equipe."
          actionLabel="Abrir primeiro chamado"
          onAction={() => setDrawerOpen(true)}
        />
      ) : (
        <>
          <div
            className={cn(
              "transition-opacity",
              isFetching && !isLoading ? "opacity-60" : "opacity-100",
            )}
          >
            <TicketsTable
              tickets={items}
              obraName={obraName}
              loading={isLoading}
              deletingId={deletingId}
              onDelete={(t: Ticket) => deleteTicket.mutate(t.id)}
            />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {pageNumber}
              {items.length > 0 ? ` · ${items.length} chamados` : ""}
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

      <CreateTicketDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </div>
  );
}
