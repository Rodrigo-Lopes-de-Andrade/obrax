"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import { fotosKeys } from "@/lib/hooks/use-fotos";

interface Subscription {
  unsubscribe(): void;
}

/**
 * Assina o canal de realtime das fotos de uma obra (F8.6). Espelha a decisão do
 * backend (app/integrations/events.py): em dev/mock não há Supabase configurado
 * (`NEXT_PUBLIC_SUPABASE_URL` vazio) → assinatura no-op, e a galeria se atualiza
 * pela confirmação local (reconcile). Em staging/prod, aqui entra
 * `supabase.channel('obra:${obraId}:fotos').on('broadcast', ...)`.
 */
function subscribeObraFotos(obraId: string, onFoto: () => void): Subscription {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  if (!url) return { unsubscribe() {} };
  // Ponto de extensão prod: assinar o canal Supabase e chamar `onFoto` no evento
  // `foto.sincronizada`. Mantido inerte enquanto sem credenciais.
  void obraId;
  void onFoto;
  return { unsubscribe() {} };
}

/** Invalida a galeria quando outra pessoa sincroniza uma foto na mesma obra —
 * a nova foto aparece em <1s nos aparelhos conectados. */
export function useObraFotosRealtime(obraId: string): void {
  const qc = useQueryClient();
  React.useEffect(() => {
    if (!obraId) return;
    const sub = subscribeObraFotos(obraId, () =>
      qc.invalidateQueries({ queryKey: fotosKeys.list(obraId) }),
    );
    return () => sub.unsubscribe();
  }, [obraId, qc]);
}
