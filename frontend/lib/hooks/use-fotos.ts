"use client";

import { useQuery } from "@tanstack/react-query";

import { getPhotos } from "@/lib/api/fotos";

export const fotosKeys = {
  all: ["fotos"] as const,
  list: (obraId: string) => ["fotos", obraId] as const,
};

/** Galeria da obra (fotos já sincronizadas no servidor). As pendentes de upload
 * vêm da fila local (Dexie) e são sobrepostas na view. */
export function useObraFotos(obraId: string) {
  return useQuery({
    queryKey: fotosKeys.list(obraId),
    queryFn: () => getPhotos(obraId),
    enabled: obraId !== "",
  });
}
