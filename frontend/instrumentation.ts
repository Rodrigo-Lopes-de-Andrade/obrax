/**
 * Sentry no server (F11.5) — gated. `register` roda uma vez no boot do server;
 * `onRequestError` captura erros de Server Components / route handlers. Ambos
 * no-op sem `SENTRY_DSN` (ou `NEXT_PUBLIC_SENTRY_DSN`). O SDK só entra no bundle
 * server, sem impacto no budget do client.
 */
const SERVER_DSN = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;

export async function register(): Promise<void> {
  if (!SERVER_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.init({
    dsn: SERVER_DSN,
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENV ?? "production",
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.1"),
    sendDefaultPii: false,
  });
}

export async function onRequestError(
  ...args: Parameters<
    typeof import("@sentry/nextjs")["captureRequestError"]
  >
): Promise<void> {
  if (!SERVER_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(...args);
}
