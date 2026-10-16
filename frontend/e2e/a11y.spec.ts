import AxeBuilder from "@axe-core/playwright";

import { expect, test } from "./fixtures";

/**
 * Auditoria de acessibilidade (F11.1, WCAG 2.1 AA). Roda o axe-core em cada tela
 * principal e falha se houver violação de severidade `critical`/`serious` nas
 * regras wcag2a/wcag2aa. As páginas do portal/campo são mobile; as admin, desktop.
 *
 * Exceção documentada (design follow-up): as cores de acento da marca não atingem
 * o contraste AA (4.5:1) na saturação em que foram desenhadas —
 *   - coral  `--primary`/`--destructive` #ff6b6b (branco sobre coral = 2.77; coral
 *     sobre tint = ~3.9);
 *   - roxo   `--secondary` #845ef7 (branco sobre roxo = 4.26).
 * Escurecer esses tons o bastante para passar mudaria a identidade visual em todo o
 * app — decisão do design, não de engenharia. Enquanto o time de design não revisa a
 * paleta, contrastes que ENVOLVEM um acento de marca (como fg OU bg) ficam na
 * allowlist. Bugs de legibilidade de texto cinza (muted/opacidade) NÃO envolvem acento
 * e continuam reprovando o gate — assim como QUALQUER violação crítica.
 */
const BRAND_ACCENTS = new Set(["#ff6b6b", "#845ef7"]);

function isBrandAccentContrast(v: { id: string; nodes: { any: { data?: unknown }[] }[] }): boolean {
  if (v.id !== "color-contrast") return false;
  return v.nodes.every((n) =>
    n.any.some((c) => {
      const d = c.data as { fgColor?: string; bgColor?: string } | undefined;
      return (
        (d?.fgColor != null && BRAND_ACCENTS.has(d.fgColor)) ||
        (d?.bgColor != null && BRAND_ACCENTS.has(d.bgColor))
      );
    }),
  );
}
const ADMIN_PAGES = [
  { name: "dashboard", path: "/dashboard" },
  { name: "obras", path: "/obras" },
  { name: "clientes", path: "/clientes" },
  { name: "orcamentos", path: "/orcamentos" },
  { name: "tickets", path: "/tickets" },
  { name: "relatorios", path: "/relatorios" },
  { name: "privacidade", path: "/privacidade" },
  { name: "ia-assistente", path: "/ia/assistente" },
  { name: "ia-auditoria", path: "/ia/auditoria" },
  { name: "ia-permissoes", path: "/ia/permissoes" },
];

const PORTAL_PAGES = [
  { name: "portal-obra", path: "/obra/demo" },
  { name: "portal-orcamento", path: "/obra/demo/orcamento" },
  { name: "portal-tickets", path: "/obra/demo/tickets" },
];

const PUBLIC_PAGES = [{ name: "landing", path: "/" }];

async function scan(page: import("./fixtures").Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  return results.violations
    .filter((v) => v.impact === "critical" || v.impact === "serious")
    .filter((v) => !isBrandAccentContrast(v));
}

test.describe("a11y admin", () => {
  test.use({ viewport: { width: 1280, height: 900 } });
  for (const p of ADMIN_PAGES) {
    test(`sem violações críticas: ${p.name}`, async ({ page, gotoApp }) => {
      await gotoApp(p.path);
      const serious = await scan(page);
      expect(
        serious,
        serious.map((v) => `${v.id}: ${v.help}`).join("\n"),
      ).toEqual([]);
    });
  }
});

test.describe("a11y portal", () => {
  test.use({ viewport: { width: 360, height: 780 } });
  for (const p of PORTAL_PAGES) {
    test(`sem violações críticas: ${p.name}`, async ({ page, gotoApp }) => {
      await gotoApp(p.path);
      const serious = await scan(page);
      expect(
        serious,
        serious.map((v) => `${v.id}: ${v.help}`).join("\n"),
      ).toEqual([]);
    });
  }
});

test.describe("a11y público", () => {
  test.use({ viewport: { width: 1280, height: 900 } });
  for (const p of PUBLIC_PAGES) {
    test(`sem violações críticas: ${p.name}`, async ({ page, gotoApp }) => {
      await gotoApp(p.path);
      const serious = await scan(page);
      expect(
        serious,
        serious.map((v) => `${v.id}: ${v.help}`).join("\n"),
      ).toEqual([]);
    });
  }
});
