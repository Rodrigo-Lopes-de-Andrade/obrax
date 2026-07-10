"use client";

import * as React from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { CheckCircle2, Loader2, RotateCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  discardMutation,
  offlineDB,
  retryAllFailed,
  retryMutation,
  type MutationStatus,
} from "@/lib/offline/db";
import { flushQueue } from "@/lib/offline/sync";
import { cn } from "@/lib/utils";

const STATUS_META: Record<MutationStatus, { label: string; cls: string }> = {
  pending: { label: "Pendente", cls: "text-amber-500" },
  uploading: { label: "Enviando", cls: "text-secondary" },
  failed: { label: "Falha", cls: "text-primary" },
};

export function OfflineQueueView() {
  const mutations = useLiveQuery(
    () =>
      offlineDB.mutations
        .toArray()
        .then((all) => all.sort((a, b) => a.createdAt - b.createdAt)),
    [],
    [],
  );
  const [busy, setBusy] = React.useState(false);

  const failed = mutations.filter((m) => m.status === "failed").length;

  const sincronizar = async () => {
    setBusy(true);
    if (failed > 0) await retryAllFailed();
    await flushQueue();
    setBusy(false);
  };

  return (
    <div>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Sincronização</h1>
          <p className="text-sm text-muted-foreground">
            {mutations.length === 0
              ? "Nenhuma alteração pendente."
              : `${mutations.length} alteraç${mutations.length === 1 ? "ão" : "ões"} na fila`}
          </p>
        </div>
        {mutations.length > 0 ? (
          <Button size="sm" onClick={sincronizar} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : <RotateCw />}
            {failed > 0 ? "Tentar todas" : "Sincronizar"}
          </Button>
        ) : null}
      </div>

      {mutations.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-border px-4 py-12 text-center">
          <CheckCircle2 className="size-9 text-success" />
          <p className="text-sm font-medium">Tudo sincronizado</p>
          <p className="text-sm text-muted-foreground">
            As alterações feitas em campo aparecem aqui até serem enviadas.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {mutations.map((m) => {
            const meta = STATUS_META[m.status];
            return (
              <li
                key={m.id}
                className="flex items-center gap-3 rounded-xl border border-border bg-card px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{m.label}</div>
                  <div className={cn("text-xs font-medium", meta.cls)}>
                    {meta.label}
                    {m.attempts > 0 ? ` · ${m.attempts} tentativa${m.attempts === 1 ? "" : "s"}` : ""}
                  </div>
                </div>
                {m.status === "failed" && m.id != null ? (
                  <>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => retryMutation(m.id!).then(() => flushQueue())}
                      aria-label="Tentar novamente"
                    >
                      <RotateCw />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => discardMutation(m.id!)}
                      aria-label="Descartar"
                    >
                      <Trash2 />
                    </Button>
                  </>
                ) : m.status === "uploading" ? (
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
