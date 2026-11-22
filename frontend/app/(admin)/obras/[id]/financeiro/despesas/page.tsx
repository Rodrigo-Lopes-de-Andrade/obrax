"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { ChevronLeft, ChevronRight, Plus, Receipt } from "lucide-react";

import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DespesasTable } from "@/components/modules/financeiro/DespesasTable";
import type { DespesaOut, DespesaStatus } from "@/lib/api/types";
import {
  useCancelarDespesa,
  useDespesas,
  useEstornarDespesa,
} from "@/lib/hooks/use-despesas";
import { useMe } from "@/lib/hooks/use-session";
import { cn } from "@/lib/utils";

// Code-split: drawer e dialog carregam sob demanda, fora do bundle inicial da rota.
const DespesaFormDrawer = dynamic(() =>
  import("@/components/modules/financeiro/DespesaFormDrawer").then((m) => m.DespesaFormDrawer),
);
const PagamentoDialog = dynamic(() =>
  import("@/components/modules/financeiro/PagamentoDialog").then((m) => m.PagamentoDialog),
);

const PAGE_SIZE = 30;
// ESPEC §9: FIN paga, cancela e estorna; gestor só lança e edita (E-10).
const FIN_ROLES = new Set(["owner", "admin", "financeiro"]);
const EDIT_ROLES = new Set(["owner", "admin", "financeiro", "gestor"]);

export default function DespesasPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: obraId } = React.use(params);
  const [statusFilter, setStatusFilter] = React.useState<DespesaStatus | "todos">("todos");
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<DespesaOut | null>(null);
  const [pagando, setPagando] = React.useState<DespesaOut | null>(null);

  const { data: me } = useMe();
  const canFin = me ? FIN_ROLES.has(me.role) : false;
  const canEdit = me ? EDIT_ROLES.has(me.role) : false;

  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;
  const status = statusFilter === "todos" ? undefined : statusFilter;
  const { data, isLoading, isFetching, isError, refetch } = useDespesas(obraId, {
    status,
    cursor,
    limit: PAGE_SIZE,
  });
  const cancelar = useCancelarDespesa(obraId);
  const estornar = useEstornarDespesa(obraId);

  const items = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const showEmpty = !isLoading && !isError && items.length === 0 && !canPrev;

  function openCreate() {
    setEditing(null);
    setDrawerOpen(true);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Despesas</h2>
          <p className="text-sm text-muted-foreground">
            Lançamentos da obra, apropriados por fase e categoria.
          </p>
        </div>
        {canEdit ? (
          <Button onClick={openCreate}>
            <Plus />
            Lançar despesa
          </Button>
        ) : null}
      </div>

      <Select
        value={statusFilter}
        onValueChange={(v) => {
          setStatusFilter(v as DespesaStatus | "todos");
          setCursorStack([]);
        }}
      >
        <SelectTrigger size="sm" className="w-44" aria-label="Filtrar por status">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="todos">Todos os status</SelectItem>
          <SelectItem value="prevista">Previstas</SelectItem>
          <SelectItem value="paga">Pagas</SelectItem>
          <SelectItem value="cancelada">Canceladas</SelectItem>
        </SelectContent>
      </Select>

      {isError ? (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive"
        >
          <span>Não foi possível carregar as despesas.</span>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : showEmpty ? (
        <EmptyState
          icon={Receipt}
          title={status ? "Nenhuma despesa com esse status" : "Nenhuma despesa lançada"}
          description="Lance a primeira despesa para acompanhar para onde o dinheiro da obra está indo."
          actionLabel={canEdit ? "Lançar primeira despesa" : undefined}
          onAction={canEdit ? openCreate : undefined}
        />
      ) : (
        <>
          <div className={cn("transition-opacity", isFetching && !isLoading ? "opacity-60" : "opacity-100")}>
            <DespesasTable
              items={items}
              loading={isLoading}
              canFin={canFin}
              canEdit={canEdit}
              onEdit={(d) => {
                setEditing(d);
                setDrawerOpen(true);
              }}
              onPagar={setPagando}
              onCancelar={(d) => cancelar.mutate(d.id)}
              onEstornar={(d) => estornar.mutate(d.id)}
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {cursorStack.length + 1}
              {items.length > 0 ? ` · ${items.length} despesas` : ""}
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

      {drawerOpen ? (
        <DespesaFormDrawer
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          obraId={obraId}
          despesa={editing}
        />
      ) : null}
      <PagamentoDialog despesa={pagando} obraId={obraId} onClose={() => setPagando(null)} />
    </div>
  );
}
