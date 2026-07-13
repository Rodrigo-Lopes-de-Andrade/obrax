/**
 * Monitoramento de erros (F11.5) — seam sem dependência no caminho default.
 *
 * `captureError` é o ponto único por onde erros não tratados passam. Com
 * `NEXT_PUBLIC_SENTRY_DSN` definido, roteia para o Sentry (`captureException`);
 * sem a DSN, o import é dead-code (tree-shaken, ver F11.3) e cai no sink de
 * analytics (PostHog, que também aceita exceções). O SDK é iniciado em
 * `instrumentation-client.ts` (client) e `instrumentation.ts` (server).
 *
 * `installGlobalErrorHandlers` liga os handlers globais do browser uma única vez
 * (idempotente). Chamado pelo componente `WebVitals` no layout.
 */
import { captureException } from "./analytics";

export function captureError(error: unknown, context?: Record<string, unknown>): void {
  // Check inlined (não via const) p/ o webpack fazer DCE do import quando a DSN
  // não está setada no build — senão o @sentry/nextjs vira chunk lazy morto.
  if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
    void import("@sentry/nextjs").then((Sentry) =>
      Sentry.captureException(error, { extra: context }),
    );
    return;
  }
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
