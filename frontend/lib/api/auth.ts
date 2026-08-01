import { useAuth } from "@/state/auth";

import { api } from "./client";

interface AccessTokenResponse {
  access_token: string;
  expires_in: number;
}

/** Autentica por e-mail + senha e guarda o access token. O refresh vem num cookie
 * httpOnly setado pelo backend (usado transparentemente em lib/api/client.ts). */
export async function login(email: string, password: string): Promise<void> {
  const res = await api.post<AccessTokenResponse>("/api/v1/auth/login", { email, password });
  useAuth.getState().setToken(res.access_token);
}

/** Encerra a sessão: revoga o refresh no backend (best-effort) e limpa o token. */
export async function logout(): Promise<void> {
  try {
    await api.post("/api/v1/auth/logout", {});
  } catch {
    // best-effort — limpa localmente de qualquer forma
  } finally {
    useAuth.getState().clear();
  }
}
