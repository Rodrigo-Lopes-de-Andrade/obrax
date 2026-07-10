"use client";

import * as React from "react";
import Link from "next/link";
import { useLiveQuery } from "dexie-react-hooks";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, CloudOff, Loader2, Plus, RotateCw } from "lucide-react";

import { ObraTabs } from "@/components/field/ObraTabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChecklistItem } from "@/lib/api/types";
import { useObra } from "@/lib/hooks/use-obras";
import { checklistKeys, useAddChecklistItem, useChecklist } from "@/lib/hooks/use-checklist";
import { enqueueChecklistToggle, offlineDB, retryMutation, type MutationStatus } from "@/lib/offline/db";
import { flushQueue } from "@/lib/offline/sync";
import { cn } from "@/lib/utils";
import { useFieldStore } from "@/state/field";

interface PendingToggle {
  mutationId: number;
  completed: boolean;
  status: MutationStatus;
}

export function ChecklistView({ obraId }: { obraId: string }) {
  const qc = useQueryClient();
  const obraQuery = useObra(obraId);
  const listQuery = useChecklist(obraId);
  const addItem = useAddChecklistItem(obraId);
  const setLastObra = useFieldStore((s) => s.setLastObra);

  const [novo, setNovo] = React.useState("");

  // Memoriza a obra p/ a aba "Checklist" da BottomNav voltar direto a ela.
  React.useEffect(() => setLastObra(obraId), [obraId, setLastObra]);

  // Overlay das mutações locais (toggles) por item — dirige o estado otimista.
  const pendingList = useLiveQuery(
    () => offlineDB.mutations.where("type").equals("checklist.toggle").toArray(),
    [],
    [],
  );
  const pending = React.useMemo(() => {
    const map = new Map<string, PendingToggle>();
    for (const m of pendingList) {
      if (m.id != null) {
        map.set(m.entityId, {
          mutationId: m.id,
          completed: Boolean(m.payload.completed),
          status: m.status,
        });
      }
    }
    return map;
  }, [pendingList]);

  const reconcile = React.useCallback(() => {
    flushQueue().finally(() => qc.invalidateQueries({ queryKey: checklistKeys.list(obraId) }));
  }, [qc, obraId]);

  const toggle = async (item: ChecklistItem, atual: boolean) => {
    await enqueueChecklistToggle({ itemId: item.id, completed: !atual, label: item.titulo });
    reconcile();
  };

  const retry = async (mutationId: number) => {
    await retryMutation(mutationId);
    reconcile();
  };

  const submitNovo = (e: React.FormEvent) => {
    e.preventDefault();
    const titulo = novo.trim();
    if (!titulo) return;
    addItem.mutate(titulo, { onSuccess: () => setNovo("") });
  };

  const items = listQuery.data?.items ?? [];
  const feitos = items.filter((i) => estado(i, pending)).length;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="outline" size="icon-sm" asChild aria-label="Voltar">
          <Link href="/campo">
            <ArrowLeft />
          </Link>
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-extrabold tracking-tight">Checklist do dia</h1>
          <p className="truncate text-xs text-muted-foreground">
            {obraQuery.data ? `${obraQuery.data.codigo} · ${obraQuery.data.nome}` : "—"}
          </p>
        </div>
      </div>

      <ObraTabs obraId={obraId} />

      {!listQuery.isLoading && items.length > 0 ? (
        <div className="mb-3 flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
          <span className="text-muted-foreground">Progresso do dia</span>
          <span className="font-semibold tabular-nums">
            {feitos}/{items.length}
          </span>
        </div>
      ) : null}

      {listQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-6 text-center text-sm text-muted-foreground">
          Não foi possível carregar o checklist.
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border px-4 py-10 text-center text-sm text-muted-foreground">
          Nenhum item no checklist ainda. Adicione o primeiro abaixo.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <ChecklistRow
              key={item.id}
              item={item}
              pending={pending.get(item.id)}
              onToggle={toggle}
              onRetry={retry}
            />
          ))}
        </ul>
      )}

      <form onSubmit={submitNovo} className="mt-4 flex gap-2">
        <Input
          value={novo}
          onChange={(e) => setNovo(e.target.value)}
          placeholder="Adicionar item ao checklist"
          className="h-11"
        />
        <Button type="submit" size="lg" disabled={!novo.trim() || addItem.isPending}>
          {addItem.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
        </Button>
      </form>
    </div>
  );
}

/** Estado exibido = overlay local (se houver) senão a verdade do servidor. */
function estado(item: ChecklistItem, pending: Map<string, PendingToggle>): boolean {
  return pending.get(item.id)?.completed ?? item.completed;
}

function ChecklistRow({
  item,
  pending,
  onToggle,
  onRetry,
}: {
  item: ChecklistItem;
  pending?: PendingToggle;
  onToggle: (item: ChecklistItem, atual: boolean) => void;
  onRetry: (mutationId: number) => void;
}) {
  const done = pending?.completed ?? item.completed;
  const falhou = pending?.status === "failed";

  return (
    <li>
      <div
        className={cn(
          "flex min-h-[56px] items-center gap-3 rounded-xl border px-3 py-2.5",
          done ? "border-border bg-card" : "border-border bg-card",
        )}
      >
        <button
          type="button"
          onClick={() => onToggle(item, done)}
          aria-pressed={done}
          aria-label={done ? "Desmarcar" : "Marcar como concluído"}
          className={cn(
            "flex size-8 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors",
            done ? "border-success bg-success text-white" : "border-muted-foreground/40",
          )}
        >
          {done ? <Check className="size-4.5" strokeWidth={3} /> : null}
        </button>

        <button
          type="button"
          onClick={() => onToggle(item, done)}
          className="min-w-0 flex-1 text-left"
        >
          <span
            className={cn(
              "block text-[15px] leading-snug",
              done && "text-muted-foreground line-through",
            )}
          >
            {item.titulo}
          </span>
          {pending ? (
            <span
              className={cn(
                "mt-0.5 inline-flex items-center gap-1 text-[11px] font-medium",
                falhou ? "text-primary" : "text-amber-500",
              )}
            >
              <CloudOff className="size-3" />
              {falhou ? "Falha ao sincronizar" : "Pendente de sincronização"}
            </span>
          ) : null}
        </button>

        {falhou && pending ? (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onRetry(pending.mutationId)}
            aria-label="Tentar sincronizar novamente"
          >
            <RotateCw />
          </Button>
        ) : null}
      </div>
    </li>
  );
}
