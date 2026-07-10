"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Loader2,
  MapPin,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { ObraTabs } from "@/components/field/ObraTabs";
import { PhotoCapture, type CapturedPhoto } from "@/components/field/PhotoCapture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { confirmPhoto, syncPhoto, uploadToStorage } from "@/lib/api/fotos";
import type { Ocorrencia } from "@/lib/api/types";
import { useObra } from "@/lib/hooks/use-obras";
import {
  useCreateOcorrencia,
  useOcorrencias,
  useUpdateOcorrenciaStatus,
} from "@/lib/hooks/use-ocorrencias";
import { sha256Hex } from "@/lib/offline/photo-hash";
import { cn } from "@/lib/utils";
import { useFieldStore } from "@/state/field";

interface Evidencia extends CapturedPhoto {
  clientPhotoId: string;
  sha256: string;
}

/** Sobe a evidência (sync → PUT → confirm) e devolve o photo_id do servidor. */
async function uploadEvidencia(obraId: string, ev: Evidencia): Promise<string> {
  const { photo_id, upload_url } = await syncPhoto(
    {
      obra_id: obraId,
      sha256: ev.sha256,
      size_bytes: ev.file.size,
      captured_at: new Date().toISOString(),
    },
    ev.clientPhotoId,
  );
  await uploadToStorage(upload_url, ev.file);
  await confirmPhoto(photo_id);
  return photo_id;
}

export function OcorrenciaView({ obraId }: { obraId: string }) {
  const obraQuery = useObra(obraId);
  const listQuery = useOcorrencias(obraId);
  const create = useCreateOcorrencia(obraId);
  const setLastObra = useFieldStore((s) => s.setLastObra);

  const [titulo, setTitulo] = React.useState("");
  const [descricao, setDescricao] = React.useState("");
  const [gps, setGps] = React.useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [evidencias, setEvidencias] = React.useState<Evidencia[]>([]);

  React.useEffect(() => setLastObra(obraId), [obraId, setLastObra]);
  // Revoga previews ao desmontar.
  React.useEffect(
    () => () => evidencias.forEach((e) => URL.revokeObjectURL(e.previewUrl)),
    [evidencias],
  );

  const onCapture = async (photo: CapturedPhoto) => {
    const sha256 = await sha256Hex(photo.file);
    setEvidencias((prev) => [...prev, { ...photo, clientPhotoId: crypto.randomUUID(), sha256 }]);
  };

  const removeEvidencia = (clientPhotoId: string) => {
    setEvidencias((prev) => {
      const alvo = prev.find((e) => e.clientPhotoId === clientPhotoId);
      if (alvo) URL.revokeObjectURL(alvo.previewUrl);
      return prev.filter((e) => e.clientPhotoId !== clientPhotoId);
    });
  };

  const usarLocalizacao = () => {
    if (!("geolocation" in navigator)) {
      toast.error("Localização indisponível neste aparelho");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocating(false);
      },
      () => {
        toast.error("Não foi possível obter a localização");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

  const podeEnviar = titulo.trim().length > 0 && evidencias.length > 0;
  const enviando = uploading || create.isPending;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!podeEnviar || enviando) return;
    setUploading(true);
    try {
      // Foto obrigatória: as evidências sobem primeiro (viram photo_id no servidor).
      const photoIds: string[] = [];
      for (const ev of evidencias) photoIds.push(await uploadEvidencia(obraId, ev));
      create.mutate(
        {
          titulo: titulo.trim(),
          descricao: descricao.trim() || null,
          gps_lat: gps?.lat ?? null,
          gps_lng: gps?.lng ?? null,
          photo_ids: photoIds,
        },
        {
          onSuccess: () => {
            evidencias.forEach((ev) => URL.revokeObjectURL(ev.previewUrl));
            setTitulo("");
            setDescricao("");
            setGps(null);
            setEvidencias([]);
            toast.success("Ocorrência registrada");
          },
        },
      );
    } catch {
      toast.error("Falha ao enviar as fotos — verifique a conexão");
    } finally {
      setUploading(false);
    }
  };

  const items = listQuery.data?.items ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="outline" size="icon-sm" asChild aria-label="Voltar">
          <Link href="/campo">
            <ArrowLeft />
          </Link>
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-extrabold tracking-tight">Ocorrências</h1>
          <p className="truncate text-xs text-muted-foreground">
            {obraQuery.data ? `${obraQuery.data.codigo} · ${obraQuery.data.nome}` : "—"}
          </p>
        </div>
      </div>

      <ObraTabs obraId={obraId} />

      <form
        onSubmit={onSubmit}
        className="mb-6 space-y-3 rounded-xl border border-border bg-card p-3"
      >
        <Input
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="Título (ex.: Infiltração na laje)"
          className="h-11"
          maxLength={200}
        />
        <Textarea
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
          placeholder="Descrição do problema (opcional)"
          rows={3}
          maxLength={5000}
        />

        {evidencias.length > 0 ? (
          <ul className="grid grid-cols-3 gap-2">
            {evidencias.map((ev) => (
              <li key={ev.clientPhotoId} className="relative overflow-hidden rounded-lg border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={ev.previewUrl}
                  alt="Evidência"
                  className="aspect-square w-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => removeEvidencia(ev.clientPhotoId)}
                  aria-label="Remover foto"
                  className="absolute right-1 top-1 rounded-full bg-background/90 p-1 text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <PhotoCapture onCapture={onCapture} variant="outline">
            {evidencias.length ? "Adicionar foto" : "Foto (obrigatória)"}
          </PhotoCapture>
          <Button
            type="button"
            variant={gps ? "secondary" : "outline"}
            size="lg"
            onClick={usarLocalizacao}
            disabled={locating}
            className="gap-2"
          >
            {locating ? <Loader2 className="animate-spin" /> : <MapPin />}
            {gps ? `${gps.lat.toFixed(4)}, ${gps.lng.toFixed(4)}` : "GPS"}
          </Button>
        </div>

        <Button type="submit" size="lg" className="w-full gap-2" disabled={!podeEnviar || enviando}>
          {enviando ? <Loader2 className="animate-spin" /> : <AlertTriangle />}
          {enviando ? "Registrando…" : "Registrar ocorrência"}
        </Button>
        {!evidencias.length ? (
          <p className="text-center text-[11px] text-muted-foreground">
            Toque em “Foto” para anexar a evidência obrigatória.
          </p>
        ) : null}
      </form>

      <h2 className="mb-2 text-sm font-semibold text-muted-foreground">Registradas</h2>
      {listQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border px-4 py-8 text-center text-sm text-muted-foreground">
          Nenhuma ocorrência registrada nesta obra.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((oc) => (
            <OcorrenciaCard key={oc.id} oc={oc} obraId={obraId} />
          ))}
        </ul>
      )}
    </div>
  );
}

function OcorrenciaCard({ oc, obraId }: { oc: Ocorrencia; obraId: string }) {
  const update = useUpdateOcorrenciaStatus(obraId);
  const resolvido = oc.status === "resolvido";

  return (
    <li className="rounded-xl border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold">{oc.titulo}</p>
          {oc.descricao ? (
            <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{oc.descricao}</p>
          ) : null}
        </div>
        <span
          className={cn(
            "flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold",
            resolvido ? "bg-success/15 text-success" : "bg-amber-500/15 text-amber-600",
          )}
        >
          {resolvido ? "Resolvido" : "Aberto"}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
        <span>
          {oc.photo_ids.length} foto{oc.photo_ids.length === 1 ? "" : "s"}
        </span>
        {oc.gps_lat != null && oc.gps_lng != null ? (
          <span className="inline-flex items-center gap-1">
            <MapPin className="size-3" />
            {oc.gps_lat.toFixed(4)}, {oc.gps_lng.toFixed(4)}
          </span>
        ) : null}
        <button
          type="button"
          onClick={() =>
            update.mutate({ id: oc.id, status: resolvido ? "aberto" : "resolvido" })
          }
          disabled={update.isPending}
          className="ml-auto inline-flex items-center gap-1 font-semibold text-foreground disabled:opacity-50"
        >
          {update.isPending ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <Check className="size-3" />
          )}
          {resolvido ? "Reabrir" : "Resolver"}
        </button>
      </div>
    </li>
  );
}
