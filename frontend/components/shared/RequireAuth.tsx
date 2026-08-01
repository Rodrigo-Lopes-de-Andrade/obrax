"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/state/auth";

/** Gate client-side das áreas autenticadas: sem access token, redireciona para
 * `/login`. Renderiza `null` até o efeito rodar (mesmo output no server e no
 * primeiro render do client → sem mismatch de hidratação), evitando flash do
 * conteúdo protegido. O token é rehidratado do localStorage pelo `persist`. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useAuth((s) => s.accessToken);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [token, router]);

  if (!ready) return null;
  return <>{children}</>;
}
