"use client";

import * as React from "react";
import Link from "next/link";
import { useLiveQuery } from "dexie-react-hooks";
import { Check, CloudOff, Loader2, RotateCw } from "lucide-react";

import { offlineDB, retryAllFailed } from "@/lib/offline/db";
import { flushQueue } from "@/lib/offline/sync";
import { cn } from "@/lib/utils";

function useOnline(): boolean {
  const [online, setOnline] = React.useState(true);
  React.useEffect(() => {
    setOnline(navigator.onLine);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

/** Indicador de sync (top-right, F7.6). Não-intrusivo quando tudo está em dia;
 * vira um botão de retry quando há falhas. */
export function SyncStatusBadge() {
  const online = useOnline();
  const counts = useLiveQuery(
    async () => {
      const all = await offlineDB.mutations.toArray();
      return {
        pending: all.filter((m) => m.status === "pending" || m.status === "uploading").length,
        failed: all.filter((m) => m.status === "failed").length,
      };
    },
    [],
    { pending: 0, failed: 0 },
  );

  const [retrying, setRetrying] = React.useState(false);
  const retry = async () => {
    setRetrying(true);
    await retryAllFailed();
    await flushQueue();
    setRetrying(false);
  };

  // Falhas → botão de retry vermelho (ação direta no header).
  if (counts.failed > 0) {
    return (
      <button
        type="button"
        onClick={retry}
        disabled={retrying}
        className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full bg-primary/12 px-3 text-xs font-semibold text-primary"
        aria-label={`${counts.failed} falha(s) — tentar novamente`}
      >
        {retrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
        {counts.failed} {counts.failed === 1 ? "falha" : "falhas"}
      </button>
    );
  }

  const base =
    "inline-flex min-h-[36px] items-center gap-1.5 rounded-full px-3 text-xs font-semibold";

  // Pendências (sincronizando ou aguardando rede).
  if (counts.pending > 0) {
    return (
      <Link href="/campo/offline" className={cn(base, "bg-amber-500/12 text-amber-500")}>
        {online ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <CloudOff className="size-3.5" />
        )}
        {counts.pending} pendente{counts.pending === 1 ? "" : "s"}
      </Link>
    );
  }

  // Offline sem fila.
  if (!online) {
    return (
      <span className={cn(base, "bg-muted text-muted-foreground")}>
        <CloudOff className="size-3.5" /> Offline
      </span>
    );
  }

  // Tudo sincronizado — discreto.
  return (
    <Link href="/campo/offline" className={cn(base, "text-muted-foreground")}>
      <Check className="size-3.5 text-success" /> Sincronizado
    </Link>
  );
}
