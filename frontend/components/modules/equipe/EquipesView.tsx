"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, Plus, Users } from "lucide-react";

import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { useMembros, useRemoveMembro } from "@/lib/hooks/use-membros";
import { cn } from "@/lib/utils";
import { AddMembroDrawer } from "./AddMembroDrawer";
import { MembrosTable } from "./MembrosTable";

const PAGE_SIZE = 50;

export function EquipesView({ obraId }: { obraId: string }) {
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;
  const { data, isLoading, isFetching, isError } = useMembros(obraId, {
    cursor,
    limit: PAGE_SIZE,
  });
  const removeMembro = useRemoveMembro(obraId);

  const items = React.useMemo(() => data?.items ?? [], [data]);
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const removingId = removeMembro.isPending
    ? (removeMembro.variables ?? null)
    : null;
  const existingUserIds = React.useMemo(
    () => new Set(items.map((m) => m.user_id)),
    [items],
  );
  const showEmpty = !isLoading && items.length === 0 && !canPrev;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Equipe</h2>
          <p className="text-sm text-muted-foreground">
            Pessoas alocadas nesta obra e seus papéis.
          </p>
        </div>
        <Button onClick={() => setDrawerOpen(true)}>
          <Plus />
          Adicionar membro
        </Button>
      </div>

      {isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Não foi possível carregar a equipe. Tente novamente.
        </div>
      ) : showEmpty ? (
        <EmptyState
          icon={Users}
          title="Nenhum membro ainda"
          description="Adicione pessoas da empresa à equipe desta obra."
          actionLabel="Adicionar primeiro membro"
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
            <MembrosTable
              membros={items}
              loading={isLoading}
              removingId={removingId}
              onRemove={(m) => removeMembro.mutate(m.user_id)}
            />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {cursorStack.length + 1}
              {items.length > 0 ? ` · ${items.length} membros` : ""}
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

      <AddMembroDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        obraId={obraId}
        existingUserIds={existingUserIds}
      />
    </div>
  );
}
