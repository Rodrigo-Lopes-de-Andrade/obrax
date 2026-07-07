import type { ProblemDetail } from "./types";

/**
 * Client HTTP fino sobre `fetch`. Base configurável por `NEXT_PUBLIC_API_URL`
 * (vazio = mesma origem, que o worker MSW intercepta em dev). Envia/recebe JSON
 * e mapeia erros RFC 7807 para `ApiError`.
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    credentials: "include",
  });

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
  post: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};
