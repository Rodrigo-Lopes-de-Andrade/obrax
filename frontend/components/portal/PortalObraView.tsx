"use client";

import { CalendarClock, CalendarRange, Download, FileText, ImageOff } from "lucide-react";

import { PortalNav } from "@/components/portal/PortalNav";
import { PortalObraHeader } from "@/components/portal/PortalObraHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortalObra } from "@/lib/hooks/use-portal";

/** dd/mm/aaaa a partir de "aaaa-mm-dd..." (evita deslocamento de timezone). */
function fmtData(s: string | null): string {
  if (!s) return "—";
  const [y, m, d] = s.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function PortalObraView({ token }: { token: string }) {
  const { data: obra, isLoading, isError } = usePortalObra(token);

  if (isLoading) {
    return (
      <div>
        <Skeleton className="mb-5 h-12 w-full rounded-xl" />
        <Skeleton className="mb-3 h-8 w-2/3" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }
  if (isError || !obra) {
    return (
      <div className="rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
        Não foi possível abrir o portal. O link pode ter expirado — solicite um novo à construtora.
      </div>
    );
  }

  return (
    <div>
      <PortalNav token={token} />
      <PortalObraHeader
        construtora={obra.construtora}
        nome={obra.nome}
        codigo={obra.codigo}
        status={obra.status}
      />

      {/* Andamento (timeline enxuta: início → previsão de entrega). */}
      <section className="mb-6 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <CalendarClock className="size-4" /> Início
          </div>
          <p className="mt-1 text-lg font-bold tabular-nums">{fmtData(obra.data_inicio)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <CalendarRange className="size-4" /> Previsão de entrega
          </div>
          <p className="mt-1 text-lg font-bold tabular-nums">{fmtData(obra.data_prevista_fim)}</p>
        </div>
      </section>

      {/* Documentos visíveis ao cliente. */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-bold">Documentos</h2>
        {obra.documentos.length === 0 ? (
          <p className="rounded-xl border border-border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
            Nenhum documento compartilhado ainda.
          </p>
        ) : (
          <ul className="space-y-2">
            {obra.documentos.map((d) => (
              <li
                key={d.id}
                className="flex items-center gap-3 rounded-xl border border-border bg-card px-3 py-2.5"
              >
                <FileText className="size-5 flex-shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{d.nome}</p>
                  <p className="text-xs text-muted-foreground">{d.categoria ?? d.tipo}</p>
                </div>
                {d.download_url ? (
                  <a
                    href={d.download_url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Baixar ${d.nome}`}
                    className="flex size-9 flex-shrink-0 items-center justify-center rounded-lg border border-border hover:bg-muted"
                  >
                    <Download className="size-4" />
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Galeria de fotos da obra. */}
      <section>
        <h2 className="mb-2 text-sm font-bold">Fotos da obra</h2>
        {obra.fotos.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
            <ImageOff className="size-6" />
            Ainda não há fotos publicadas.
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {obra.fotos.map((f) =>
              f.download_url ? (
                <a
                  key={f.id}
                  href={f.download_url}
                  target="_blank"
                  rel="noreferrer"
                  className="aspect-square overflow-hidden rounded-lg border border-border bg-muted"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={f.download_url}
                    alt="Foto da obra"
                    className="size-full object-cover"
                  />
                </a>
              ) : null,
            )}
          </div>
        )}
      </section>
    </div>
  );
}
