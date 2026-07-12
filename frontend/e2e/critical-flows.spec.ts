import { expect, test } from "./fixtures";

/**
 * Fluxos críticos E2E (F11.4) contra o frontend mock-first (MSW). Cobrem as
 * jornadas principais dos três públicos (admin, campo, portal) e do Módulo 3.
 * Não há login: o mock injeta um usuário; as rotas são acessíveis direto.
 */

test.describe("admin", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("dashboard mostra KPIs da empresa e insights de IA", async ({ page, gotoApp }) => {
    await gotoApp("/dashboard");
    await expect(page.getByText("Indicadores da Empresa")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Agentes IA" })).toBeVisible();
  });

  test("lista de obras carrega linhas", async ({ page, gotoApp }) => {
    await gotoApp("/obras");
    await expect(page.getByRole("link", { name: /Obra/i }).first()).toBeVisible();
    await expect(page.locator("table tbody tr").first()).toBeVisible();
  });

  test("assistente IA responde a uma pergunta", async ({ page, gotoApp }) => {
    await gotoApp("/ia/assistente");
    await page.getByPlaceholder(/Pergunte ao assistente/i).fill("Qual o status da obra?");
    await page.getByRole("button", { name: "Enviar" }).click();
    await expect(page.getByText("Assistente").first()).toBeVisible();
    await expect(page.getByText(/em execução/i).first()).toBeVisible();
  });

  test("auditoria IA reverte uma ação com efeito", async ({ page, gotoApp }) => {
    await gotoApp("/ia/auditoria");
    const reverter = page.getByRole("button", { name: /Reverter/i }).first();
    await expect(reverter).toBeVisible();
    await reverter.click();
    await expect(page.getByText("Revertido").first()).toBeVisible();
  });

  test("permissões IA: autorizar um número", async ({ page, gotoApp }) => {
    await gotoApp("/ia/permissoes");
    await page.getByPlaceholder(/90000-0000/).fill("+5511955554444");
    await page.getByRole("button", { name: "Autorizar" }).click();
    await expect(page.getByText("+5511955554444")).toBeVisible();
  });

  test("privacidade: solicitar exportação LGPD", async ({ page, gotoApp }) => {
    await gotoApp("/privacidade");
    await page.getByRole("button", { name: /Solicitar exportação/i }).click();
    await expect(page.getByRole("link", { name: /Baixar ZIP/i })).toBeVisible();
  });
});

test.describe("portal do cliente", () => {
  test.use({ viewport: { width: 360, height: 780 } });

  test("timeline da obra abre com cabeçalho da construtora", async ({ page, gotoApp }) => {
    await gotoApp("/obra/demo");
    await expect(page.getByRole("navigation")).toBeVisible();
    await expect(page.getByText(/Documentos/i).first()).toBeVisible();
  });

  test("chamados: navega e lista", async ({ page, gotoApp }) => {
    await gotoApp("/obra/demo/tickets");
    await expect(page.getByRole("heading", { name: "Chamados" })).toBeVisible();
  });
});

test.describe("campo (mobile)", () => {
  test.use({ viewport: { width: 360, height: 780 } });

  test("home do campo carrega", async ({ page, gotoApp }) => {
    await gotoApp("/campo");
    await expect(page.locator("body")).toBeVisible();
    // Sem erro fatal de render: há conteúdo visível.
    await expect(page.locator("main, nav, header").first()).toBeVisible();
  });
});
