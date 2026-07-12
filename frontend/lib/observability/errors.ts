/**
 * Monitoramento de erros (F11.5) — seam sem dependência.
 *
 * `captureError` é o ponto único por onde erros não tratados passam. Hoje a rota
 * sempre-disponível é o sink de analytics (`captureException` → PostHog, que
 * também aceita exceções). Para monitoramento dedicado em produção, o caminho é
 * instalar `@sentry/nextjs` e chamar `Sentry.captureException` aqui dentro,
 * guardado por `NEXT_PUBLIC_SENTRY_DSN` — sem quebrar quem roda sem Sentry.
 *
 * `installGlobalErrorHandlers` liga os handlers globais do browser uma única vez
 * (idempotente). Chamado por um componente client no layout.
 */
import { captureException } from "./analytics";

export const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

export function captureError(error: unknown, context?: Record<string, unknown>): void {
  // Rota de produção (quando @sentry/nextjs estiver instalado + DSN definido):
  //   if (sentryDsn) { Sentry.captureException(error, { extra: context }); return; }
  captureException(error, context);
}

let installed = false;

/** Liga window.onerror e onunhandledrejection uma vez só. */
export function installGlobalErrorHandlers(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;
  window.addEventListener("error", (e) => {
    captureError(e.error ?? e.message, { source: "window.onerror" });
  });
  window.addEventListener("unhandledrejection", (e) => {
    captureError(e.reason, { source: "unhandledrejection" });
  });
}
