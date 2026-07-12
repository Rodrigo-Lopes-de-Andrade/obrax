import { test as base, expect, type Page } from "@playwright/test";

/**
 * Fixture base dos E2E. Duas responsabilidades:
 * 1. Bloqueia o service worker do PWA (`/sw.js`) — ele disputa o scope "/" com o
 *    MSW e, se vencer, manda todo /api/v1/* pra rede (404). Bloqueado, o worker
 *    do MSW controla a aba.
 * 2. `gotoApp`: navega e espera o MSW subir. Numa aba nova o SW do MSW só
 *    controla após um reload — por isso o goto→reload (ver memória do projeto).
 */
export const test = base.extend<{ gotoApp: (path: string) => Promise<void> }>({
  context: async ({ context }, use) => {
    await context.route("**/sw.js", (route) => route.fulfill({ status: 404, body: "" }));
    await use(context);
  },
  gotoApp: async ({ page }, use) => {
    const go = async (path: string) => {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(800);
      await page.reload({ waitUntil: "domcontentloaded" });
      // Espera o app renderizar (providers bloqueia o render até o MSW subir).
      await page.waitForTimeout(1500);
    };
    await use(go);
  },
});

export { expect };
export type { Page };
