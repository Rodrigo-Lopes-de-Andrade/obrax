/**
 * Sentry no client (F11.5) — gated + tree-shaken.
 *
 * `NEXT_PUBLIC_SENTRY_DSN` é inlined no build; sem ela, o bloco vira dead-code e
 * o `@sentry/nextjs` sai do bundle (preserva o budget F11.3). Com a DSN, carrega
 * o SDK sob demanda e inicia error tracking + replay-on-error + tracing, com PII
 * mascarada (sem texto/inputs/mídia no replay, sem PII default).
 *
 * Release atada ao commit: setar `NEXT_PUBLIC_SENTRY_RELEASE` no build (CI = git SHA).
 */
if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  void import("@sentry/nextjs").then((Sentry) => {
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
      environment: process.env.NEXT_PUBLIC_SENTRY_ENV ?? "production",
      // Perf monitoring: amostra configurável (default 10%).
      tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.1"),
      // Session replay: só quando há erro (0% de sessões "normais" p/ custo/privacidade).
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 1,
      // PII: nunca anexa dados pessoais por padrão e mascara todo o replay.
      sendDefaultPii: false,
      integrations: [Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true })],
    });
  });
}
