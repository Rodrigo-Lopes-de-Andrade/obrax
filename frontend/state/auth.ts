import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Sessão do usuário (persistida em localStorage). Guarda só o access token JWT;
 * o refresh vive num cookie httpOnly no backend (ver lib/api/client.ts). O tenant
 * (company_id) e o role vêm dentro do próprio JWT — a TenantMiddleware do backend
 * os lê a cada request, então o front não precisa decodificá-los para navegar. */
interface AuthState {
  accessToken: string | null;
  setToken: (token: string | null) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      setToken: (accessToken) => set({ accessToken }),
      clear: () => set({ accessToken: null }),
    }),
    { name: "obrax-auth" },
  ),
);
