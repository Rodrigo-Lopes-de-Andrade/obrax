"use client";

import * as React from "react";
import Link from "next/link";
import { useLiveQuery } from "dexie-react-hooks";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, CloudOff, ImageOff, Loader2, RotateCw } from "lucide-react";

import { ObraTabs } from "@/components/field/ObraTabs";
import { PhotoCapture, type CapturedPhoto } from "@/components/field/PhotoCapture";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fotosKeys, useObraFotos } from "@/lib/hooks/use-fotos";
import { useObra } from "@/lib/hooks/use-obras";
import {
  enqueuePhotoUpload,
  offlineDB,
  retryMutation,
  type MutationStatus,
} from "@/lib/offline/db";
import { sha256Hex } from "@/lib/offline/photo-hash";
import { flushQueue } from "@/lib/offline/sync";
import { useObraFotosRealtime } from "@/lib/realtime/obra-fotos";
import { cn } from "@/lib/utils";
import { useFieldStore } from "@/state/field";

export function FotosView({ obraId }: { obraId: string }) {
  const qc = useQueryClient();
  const obraQuery = useObra(obraId);
  const fotosQuery = useObraFotos(obraId);
  const setLastObra = useFieldStore((s) => s.setLastObra);
  useObraFotosRealtime(obraId);

  React.useEffect(() => setLastObra(obraId), [obraId, setLastObra]);

  // Blobs pendentes desta obra + status das mutações de upload (por clientPhotoId).
  const blobs = useLiveQuery(
    () => offlineDB.photos.where("obraId").equals(obraId).toArray(),
    [obraId],
    [],
  );
  const uploadMuts = useLiveQuery(
    () => offlineDB.mutations.where("type").equals("photo.upload").toArray(),
    [],
    [],
  );

  const statusByClient = React.useMemo(() => {
    const m = new Map<string, { status: MutationStatus; mutationId: number }>();
    for (const mut of uploadMuts) {
      if (mut.id != null) m.set(mut.entityId, { status: mut.status, mutationId: mut.id });
    }
    return m;
  }, [uploadMuts]);

  // Object URLs dos blobs locais — revogadas ao trocar o conjunto/desmontar.
  const localUrls = React.useMemo(() => {
    const m = new Map<string, string>();
    for (const b of blobs) m.set(b.clientPhotoId, URL.createObjectURL(b.blob));
    return m;
  }, [blobs]);
  React.useEffect(() => () => localUrls.forEach((u) => URL.revokeObjectURL(u)), [localUrls]);

  const reconcile = React.useCallback(() => {
    flushQueue().finally(() => qc.invalidateQueries({ queryKey: fotosKeys.list(obraId) }));
  }, [qc, obraId]);

  const onCapture = async ({ file, previewUrl }: CapturedPhoto) => {
    URL.revokeObjectURL(previewUrl); // a galeria cria a própria URL do blob salvo
    const sha256 = await sha256Hex(file);
    await enqueuePhotoUpload({
      clientPhotoId: crypto.randomUUID(),
      obraId,
      blob: file,
      sha256,
      sizeBytes: file.size,
      capturedAt: new Date().toISOString(),
      label: `Foto — ${obraQuery.data?.nome ?? "obra"}`,
    });
    reconcile();
  };

  const retry = async (mutationId: number) => {
    await retryMutation(mutationId);
    reconcile();
  };

  // Fotos do servidor, menos as que ainda têm blob local (evita duplicar na troca).
  const localClientIds = new Set(blobs.map((b) => b.clientPhotoId));
  const serverPhotos = (fotosQuery.data?.items ?? []).filter(
    (p) => !localClientIds.has(p.client_photo_id),
  );
  const total = blobs.length + serverPhotos.length;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="outline" size="icon-sm" asChild aria-label="Voltar">
          <Link href="/campo">
            <ArrowLeft />
          </Link>
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-extrabold tracking-tight">Fotos da obra</h1>
          <p className="truncate text-xs text-muted-foreground">
            {obraQuery.data ? `${obraQuery.data.codigo} · ${obraQuery.data.nome}` : "—"}
          </p>
        </div>
      </div>

      <ObraTabs obraId={obraId} />

      <div className="mb-4">
        <PhotoCapture onCapture={onCapture}>Tirar foto</PhotoCapture>
      </div>

      {fotosQuery.isLoading ? (
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-xl" />
          ))}
        </div>
      ) : total === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-border px-4 py-10 text-center">
          <ImageOff className="size-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            Nenhuma foto ainda. Toque em “Tirar foto”.
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-2 gap-2">
          {blobs.map((b) => (
            <LocalTile
              key={b.clientPhotoId}
              url={localUrls.get(b.clientPhotoId)}
              status={statusByClient.get(b.clientPhotoId)?.status ?? "uploading"}
              onRetry={() => {
                const s = statusByClient.get(b.clientPhotoId);
                if (s) void retry(s.mutationId);
              }}
            />
          ))}
          {serverPhotos.map((p) => (
            <li
              key={p.id}
              className="relative overflow-hidden rounded-xl border border-border bg-muted"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={p.download_url ?? ""}
                alt="Foto da obra"
                className="aspect-square w-full object-cover"
              />
              <span className="absolute bottom-1 left-1 inline-flex items-center gap-1 rounded-full bg-success/90 px-2 py-0.5 text-[10px] font-semibold text-white">
                <Check className="size-3" strokeWidth={3} /> Sincronizado
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const CHIP: Record<MutationStatus, { label: string; className: string }> = {
  uploading: { label: "Enviando", className: "bg-amber-500/90" },
  pending: { label: "Pendente", className: "bg-amber-500/90" },
  failed: { label: "Falha", className: "bg-primary/90" },
};

function LocalTile({
  url,
  status,
  onRetry,
}: {
  url?: string;
  status: MutationStatus;
  onRetry: () => void;
}) {
  const chip = CHIP[status];
  const failed = status === "failed";
  return (
    <li className="relative overflow-hidden rounded-xl border border-border bg-muted">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt="Foto pendente" className="aspect-square w-full object-cover" />
      ) : (
        <div className="aspect-square w-full" />
      )}
      <span
        className={cn(
          "absolute bottom-1 left-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold text-white",
          chip.className,
        )}
      >
        {failed ? <CloudOff className="size-3" /> : <Loader2 className="size-3 animate-spin" />}
        {chip.label}
      </span>
      {failed ? (
        <button
          type="button"
          onClick={onRetry}
          aria-label="Tentar sincronizar novamente"
          className="absolute right-1 top-1 rounded-full bg-background/90 p-1.5 text-foreground"
        >
          <RotateCw className="size-3.5" />
        </button>
      ) : null}
    </li>
  );
}
