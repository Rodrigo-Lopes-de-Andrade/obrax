"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/state/auth";

/** Gate client-side das áreas autenticadas. Sem access token → `/login`.
 *
 * Crítico: só decide DEPOIS que o `persist` (zustand) hidrata o token do
 * localStorage. Sem esperar, um refresh/entrada direta numa rota protegida
 * enxergaria `token=null` (ainda não hidratado) e deslogaria o usuário. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useAuth((s) => s.accessToken);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (useAuth.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useAuth.persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, []);

  useEffect(() => {
    if (hydrated && !token) {
      router.replace("/login");
    }
  }, [hydrated, token, router]);

  // Espera a hidratação antes de renderizar/decidir (mesmo output no server e no
  // 1º render do client → sem mismatch; evita flash e o logout indevido).
  if (!hydrated || !token) return null;
  return <>{children}</>;
}
