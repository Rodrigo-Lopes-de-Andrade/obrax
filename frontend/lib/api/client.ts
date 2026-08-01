import { useAuth } from "@/state/auth";

import type { ProblemDetail } from "./types";

/**
 * Client HTTP fino sobre `fetch`. Base configurável por `NEXT_PUBLIC_API_URL`
 * (vazio = mesma origem, que o worker MSW intercepta em dev). Envia/recebe JSON
 * e mapeia erros RFC 7807 para `ApiError`.
 *
 * Auth: injeta `Authorization: Bearer <access token>` (de `useAuth`) e, num 401,
 * tenta uma vez o `POST /auth/refresh` (cookie httpOnly) e repete a request. Se o
 * refresh falhar, limpa a sessão e manda pro `/login`.
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// Os próprios endpoints de auth não entram no fluxo de refresh (evita recursão).
const AUTH_PATHS = ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout"];

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(status: number, problem: ProblemDetail) {
    super(problem.detail ?? problem.title ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

// Single-flight: várias requests que tomam 401 ao mesmo tempo compartilham um
// único refresh em voo em vez de dispararem N chamadas.
let refreshPromise: Promise<string | null> | null = null;

function refreshToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const data = (await res.json()) as { access_token: string };
        useAuth.getState().setToken(data.access_token);
        return data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const token = useAuth.getState().accessToken;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    credentials: "include",
  });

  // 401 numa rota protegida: tenta um refresh e repete a request uma única vez.
  if (res.status === 401 && retry && !AUTH_PATHS.includes(path)) {
    const newToken = await refreshToken();
    if (newToken) return request<T>(path, init, false);
    // Sessão expirada e sem refresh válido: limpa e vai pro login.
    useAuth.getState().clear();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const isJson = res.headers.get("content-type")?.includes("json") ?? false;
  const body: unknown = isJson ? await res.json() : undefined;

  if (!res.ok) {
    const problem: ProblemDetail =
      isJson && body ? (body as ProblemDetail) : { status: res.status };
    throw new ApiError(res.status, problem);
  }

  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  // `headers` opcional: alguns POSTs exigem cabeçalho extra (ex.: Idempotency-Key
  // em /photos/sync).
  post: <T>(path: string, data: unknown, headers?: Record<string, string>) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data), headers }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  // Genérico: alguns DELETEs (ex.: remover item da EAP) devolvem a árvore
  // recalculada em vez de 204.
  delete: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
};
