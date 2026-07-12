/**
 * Analytics de produto (F11.6) — seam sem dependência de SDK.
 *
 * Padrão do projeto: no-op até ser configurado por env. Se
 * `NEXT_PUBLIC_POSTHOG_KEY` estiver definido, os eventos vão pro endpoint de
 * `/capture` do PostHog via `fetch` (fire-and-forget, `keepalive`); sem a key,
 * em dev caem num `console.debug`, em prod são descartados. Assim o build e os
 * testes rodam sem PostHog e a ativação é só setar as envs no deploy — sem
 * instalar `posthog-js` (mantém o bundle enxuto, ver F11.3).
 *
 * Ativar (deploy): NEXT_PUBLIC_POSTHOG_KEY + NEXT_PUBLIC_POSTHOG_HOST
 * (default https://us.i.posthog.com).
 */

const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";
const DEV = process.env.NODE_ENV === "development";
const DISTINCT_ID_STORAGE_KEY = "obrax:distinct_id";

export const analyticsEnabled = Boolean(KEY);

/** ID anônimo estável por navegador (não-PII). Só existe no client. */
function distinctId(): string {
  if (typeof window === "undefined") return "server";
  try {
    let id = window.localStorage.getItem(DISTINCT_ID_STORAGE_KEY);
    if (!id) {
      id = `anon_${crypto.randomUUID()}`;
      window.localStorage.setItem(DISTINCT_ID_STORAGE_KEY, id);
    }
    return id;
  } catch {
    return "anon_no_storage";
  }
}

/**
 * Registra um evento de produto. Seguro em qualquer ambiente: nunca lança e
 * nunca bloqueia o render (fire-and-forget).
 */
export function capture(event: string, properties?: Record<string, unknown>): void {
  if (typeof window === "undefined") return; // só client
  if (!KEY) {
    if (DEV) console.debug("[analytics:noop]", event, properties ?? {});
    return;
  }
  const payload = {
    api_key: KEY,
    event,
    distinct_id: distinctId(),
    properties: { $current_url: window.location.href, ...properties },
  };
  try {
    void fetch(`${HOST.replace(/\/$/, "")}/capture/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      /* telemetria não pode quebrar o app */
    });
  } catch {
    /* idem */
  }
}

/** Captura de exceção (rota de fallback do seam de erros — ver errors.ts). */
export function captureException(error: unknown, context?: Record<string, unknown>): void {
  const message = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : undefined;
  capture("$exception", { $exception_message: message, $exception_stack: stack, ...context });
}
