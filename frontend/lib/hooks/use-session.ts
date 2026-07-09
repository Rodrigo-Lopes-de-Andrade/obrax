"use client";

import { useQuery } from "@tanstack/react-query";

import { getMe } from "@/lib/api/session";

/** Usuário autenticado (mock `/me`). Estável na sessão → `staleTime` infinito. */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: Infinity,
  });
}
