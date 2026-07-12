import { defineConfig, devices } from "@playwright/test";

/**
 * E2E do frontend mock-first (F11.4). O dev server (NODE_ENV=development) é
 * obrigatório: o MSW só liga em dev (ver app/providers.tsx). As specs usam o
 * fixture `test` de e2e/fixtures.ts, que bloqueia o service worker do PWA
 * (`/sw.js`) para o worker do MSW controlar a aba (senão todo /api/v1/* vira 404).
 */
const PORT = 3111;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command: `pnpm dev -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
