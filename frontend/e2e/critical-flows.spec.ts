import { expect, test } from "./fixtures";

/**
 * Fluxos críticos E2E (F11.4) contra o frontend mock-first (MSW). Cobrem as
 * jornadas principais dos três públicos (admin, campo, portal) e do Módulo 3.
 * Não há login: a fixture semeia um token e o MSW responde o /auth/me.
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

test.describe("login", () => {
  // O MSW não mocka /auth/login (bypass); o Playwright simula a resposta do backend.
  const casos = [
    { status: 401, msg: "E-mail ou senha inválidos." },
    { status: 500, msg: /sistema está indisponível/i },
  ];
  for (const { status, msg } of casos) {
    test(`mensagem de erro para HTTP ${status}`, async ({ page, context, gotoApp }) => {
      await context.route("**/api/v1/auth/login", (route) =>
        route.fulfill({
          status,
          contentType: "application/problem+json",
          body: JSON.stringify({ status, title: "erro", detail: "erro" }),
        }),
      );
      await gotoApp("/login");
      await page.getByLabel("E-mail").fill("voce@empresa.com.br");
      await page.getByLabel("Senha").fill("qualquer-senha");
      await page.getByRole("button", { name: "Entrar" }).click();
      await expect(page.locator("form").getByRole("alert")).toHaveText(msg);
    });
  }
});

test.describe("clientes", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("cadastra um cliente pela tela de Clientes", async ({ page, gotoApp }) => {
    await gotoApp("/clientes");
    await page.getByRole("button", { name: /Novo cliente|Cadastrar primeiro cliente/ }).first().click();
    const drawer = page.getByRole("dialog");
    await drawer.getByLabel("CNPJ").fill("11222333000181");
    await drawer.getByLabel("Razão social / nome").fill("Construtora E2E Ltda");
    await drawer.getByRole("button", { name: "Cadastrar cliente" }).click();
    await expect(page.getByRole("cell", { name: "Construtora E2E Ltda" })).toBeVisible();
    await expect(page.getByText("11.222.333/0001-81")).toBeVisible();
  });

  test("CPF inválido aparece no campo, sem enviar", async ({ page, gotoApp }) => {
    await gotoApp("/clientes");
    await page.getByRole("button", { name: /Novo cliente|Cadastrar primeiro cliente/ }).first().click();
    const drawer = page.getByRole("dialog");
    await drawer.getByRole("combobox", { name: "Tipo de pessoa" }).click();
    await page.getByRole("option", { name: "Pessoa física" }).click();
    await drawer.getByLabel("CPF").fill("12345678900");
    await drawer.getByLabel("Nome", { exact: true }).fill("Fulano");
    await drawer.getByRole("button", { name: "Cadastrar cliente" }).click();
    await expect(drawer.getByText(/Documento inválido/)).toBeVisible();
  });

  test("Nova obra: atalho cadastra e já seleciona o cliente", async ({ page, gotoApp }) => {
    await gotoApp("/obras");
    await page.getByRole("button", { name: "Nova obra" }).first().click();
    await page.getByRole("button", { name: "Novo cliente" }).click();
    const clienteDrawer = page.getByRole("dialog", { name: "Novo cliente" });
    await clienteDrawer.getByLabel("CNPJ").fill("11.444.777/0001-61");
    await clienteDrawer.getByLabel("Razão social / nome").fill("Cliente Atalho Ltda");
    await clienteDrawer.getByRole("button", { name: "Cadastrar cliente" }).click();
    await expect(clienteDrawer).toBeHidden();
    await expect(
      page.getByRole("dialog", { name: "Nova obra" }).getByRole("combobox", { name: "Cliente" }),
    ).toHaveText(/Cliente Atalho Ltda/);
  });
});

test.describe("menu superior", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("busca global encontra uma obra e navega até ela", async ({ page, gotoApp }) => {
    await gotoApp("/dashboard");
    await page.getByRole("combobox", { name: "Buscar obras e clientes" }).fill("Aurora");
    const opcao = page.getByRole("option", { name: /Edifício Aurora/ }).first();
    await expect(opcao).toBeVisible();
    await opcao.click();
    await expect(page).toHaveURL(/\/obras\/[^/]+\/documentos/);
  });

  test("sino leva aos chamados e mensagens ao assistente", async ({ page, gotoApp }) => {
    await gotoApp("/dashboard");
    const header = page.getByRole("banner");
    await header.getByRole("link", { name: /^Chamados/ }).click();
    await expect(page).toHaveURL(/\/tickets$/);
    await header.getByRole("link", { name: "Assistente IA" }).click();
    await expect(page).toHaveURL(/\/ia\/assistente$/);
  });
});
