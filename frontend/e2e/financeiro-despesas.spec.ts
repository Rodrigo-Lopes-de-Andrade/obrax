import AxeBuilder from "@axe-core/playwright";

import { FINANCEIRO_EXEMPLOS } from "../lib/mock/db";
import { expect, test, type Page } from "./fixtures";

/**
 * S-F4 — telas de despesa e categorias contra o mock MSW (S-F2).
 * O mock é estático: GET devolve sempre `DespesaPage` (2 linhas, "prevista"), POST de
 * despesa devolve `DespesaOut` e o de parcelada devolve 3 parcelas "Armação (n/3)", `pagar`
 * devolve `DespesaOut#paga`. Os testes afirmam sobre o corpo enviado e sobre a UI.
 *
 * O axe roda aqui, e não em `a11y.spec.ts` (editado só na S-F11), com a MESMA allowlist de
 * contraste das cores de marca (#ff6b6b / #845ef7) daquele spec — ver o comentário lá.
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

async function scan(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return results.violations
    .filter((v) => v.impact === "critical" || v.impact === "serious")
    .filter((v) => !isBrandAccentContrast(v));
}

/** O id das obras do mock é gerado em runtime: pega o de uma obra real da lista. */
async function despesasPath(page: Page, gotoApp: (p: string) => Promise<void>): Promise<string> {
  await gotoApp("/obras");
  const href = await page.locator('table a[href^="/obras/"]').first().getAttribute("href");
  const id = /^\/obras\/([^/]+)/.exec(href ?? "")?.[1];
  expect(id).toBeTruthy();
  return `/obras/${id}/financeiro/despesas`;
}

async function abrirLancamento(page: Page) {
  await page.getByRole("button", { name: "Lançar despesa" }).click();
  await expect(page.getByRole("dialog", { name: "Lançar despesa" })).toBeVisible();
}

async function escolher(page: Page, campo: string, opcao: RegExp) {
  await page.getByRole("combobox", { name: campo }).click();
  await page.getByRole("option", { name: opcao }).click();
}

async function preencherBase(page: Page) {
  await escolher(page, "Fase", /Fundação/);
  await escolher(page, "Categoria", /Materiais/);
  await page.getByLabel("Fornecedor").fill("Concreteira Alfa");
  await page.getByLabel("Descrição").fill("Armação");
  await page.getByLabel("Competência").fill("2026-01-15");
}

test.describe("financeiro · despesas", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("lista as despesas da obra", async ({ page, gotoApp }) => {
    await gotoApp(await despesasPath(page, gotoApp));
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Aço CA-50/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toContainText("R$ 12.500,00");
  });

  test("submeter sem fase é barrado no client", async ({ page, gotoApp }) => {
    await stubFetch(page, []); // só para gravar as chamadas (tudo cai no MSW)
    await gotoApp(await despesasPath(page, gotoApp));

    await abrirLancamento(page);
    await escolher(page, "Categoria", /Materiais/);
    await page.getByLabel("Fornecedor").fill("Concreteira Alfa");
    await page.getByLabel("Descrição").fill("Concreto");
    await page.getByLabel("Valor", { exact: true }).fill("150050");
    await page.getByLabel("Competência").fill("2026-01-15");
    await page.getByLabel("Vencimento").fill("2026-02-10");
    await page.getByRole("button", { name: "Lançar despesa" }).last().click();

    // O placeholder também diz "Selecione a fase": a mensagem é afirmada no FormItem da fase.
    await expect(page.getByRole("combobox", { name: "Fase" })).toHaveAttribute("aria-invalid", "true");
    await expect(page.locator('[data-slot="form-message"]').filter({ hasText: "Selecione a fase" })).toBeVisible();
    expect(await chamadas(page, "POST", /\/despesas/)).toEqual([]);
  });

  test("seletor de fase lista as fases da obra", async ({ page, gotoApp }) => {
    await gotoApp(await despesasPath(page, gotoApp));
    await abrirLancamento(page);
    await page.getByRole("combobox", { name: "Fase" }).click();
    await expect(page.getByRole("option", { name: /01 · Fundação/ })).toBeVisible();
    await expect(page.getByRole("option", { name: /02 · Estrutura/ })).toBeVisible();
    // Só fases ativas: "03 · Cobertura" (ativa: false) não é oferecida.
    await expect(page.getByRole("option", { name: /Cobertura/ })).toHaveCount(0);
  });

  test("lançar despesa envia o decimal canônico (MoneyInput) e fecha o drawer", async ({ page, gotoApp }) => {
    await stubFetch(page, []);
    await gotoApp(await despesasPath(page, gotoApp));
    await abrirLancamento(page);
    await preencherBase(page);
    // MoneyInput: digita em centavos, exibe pt-BR.
    await page.getByLabel("Valor", { exact: true }).fill("150050");
    await expect(page.getByLabel("Valor", { exact: true })).toHaveValue(/1\.500,50/);
    await page.getByLabel("Vencimento").fill("2026-02-10");

    await page.getByRole("button", { name: "Lançar despesa" }).last().click();
    const body = await corpo(page, "POST", /\/obras\/[^/]+\/despesas$/);
    expect(body).toMatchObject({
      obra_fase_id: "01900000-0000-4000-8000-000000000015",
      categoria_id: "01900000-0000-4000-8000-00000000001f",
      fornecedor_nome: "Concreteira Alfa",
      valor: "1500.50",
      data_competencia: "2026-01-15",
      vencimento: "2026-02-10",
    });
    await expect(page.getByRole("dialog", { name: "Lançar despesa" })).toBeHidden();
  });

  test("parcelamento mostra a prévia, com o resto na última, e as parcelas entram na lista", async ({
    page,
    gotoApp,
  }) => {
    // Com refetch real após o POST, o GET seguinte já traz as parcelas (stub com estado).
    const parceladas = FINANCEIRO_EXEMPLOS.DespesaParceladaOut;
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          { status: 200, body: PAGE },
          { status: 200, body: { items: [...parceladas.parcelas, ...PAGE.items], next_cursor: null } },
        ],
      },
      um("POST", `${API_DESPESAS}/parcelada`, 201, parceladas),
    ]);
    await gotoApp(PATH);
    await abrirLancamento(page);
    await preencherBase(page);
    await page.getByLabel("Valor", { exact: true }).fill("100000");
    await page.getByLabel(/Parcelar/).click();
    await page.getByLabel("Número de parcelas").fill("3");
    await page.getByLabel("1º vencimento").fill("2026-02-10");

    const previa = page.getByRole("group", { name: "Prévia das parcelas" });
    await expect(previa).toBeVisible();
    await expect(previa.getByText("R$ 333,33")).toHaveCount(2);
    await expect(previa.getByText("R$ 333,34")).toHaveCount(1);
    await expect(previa.getByTestId("parcelas-total")).toHaveText("R$ 1.000,00");

    await page.getByRole("button", { name: "Confirmar parcelas" }).click();
    expect(await corpo(page, "POST", /\/despesas\/parcelada$/)).toMatchObject({
      valor: "1000.00",
      numero_parcelas: 3,
      primeiro_vencimento: "2026-02-10",
    });
    // As parcelas devolvidas entram na lista (cache), identificadas n/total (CA-F08.3).
    await expect(page.getByRole("row", { name: /Armação/ })).toHaveCount(3);
    await expect(page.getByRole("row", { name: /Armação.*1\/3/ })).toBeVisible();
  });

  test("prévia de 100,00 em 6 é 16,66 × 5 + 16,70 e recusa valor menor que N centavos", async ({
    page,
    gotoApp,
  }) => {
    await stubFetch(page, []);
    await gotoApp(await despesasPath(page, gotoApp));
    await abrirLancamento(page);
    await preencherBase(page);
    await page.getByLabel("Valor", { exact: true }).fill("10000");
    await page.getByLabel(/Parcelar/).click();
    await page.getByLabel("Número de parcelas").fill("6");
    await page.getByLabel("1º vencimento").fill("2026-02-10");
    const previa = page.getByRole("group", { name: "Prévia das parcelas" });
    await expect(previa.getByText("R$ 16,66")).toHaveCount(5);
    await expect(previa.getByText("R$ 16,70")).toHaveCount(1);
    await expect(previa.getByTestId("parcelas-total")).toHaveText("R$ 100,00");

    // R$ 0,05 em 6 parcelas: menos de 1 centavo por parcela, recusado no client.
    await page.getByLabel(/Valor total/).fill("5");
    await expect(page.getByRole("alert").filter({ hasText: "menor que 6 centavos" })).toBeVisible();
    await expect(previa).toHaveCount(0);
    await page.getByRole("button", { name: "Confirmar parcelas" }).click();
    await expect(page.locator('[data-slot="form-message"]').filter({ hasText: "ao menos 6 centavos" })).toBeVisible();
    expect(await chamadas(page, "POST", /\/despesas/)).toEqual([]);
  });

  test("pagar pede a data e atualiza a linha sem recarregar", async ({ page, gotoApp }) => {
    const prevista = PAGE.items[0];
    const paga = { ...prevista, status: "paga", data_pagamento: "2026-02-10" };
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          { status: 200, body: PAGE },
          { status: 200, body: { items: [paga, ...PAGE.items.slice(1)], next_cursor: null } },
        ],
      },
      um("POST", `/financeiro/despesas/${prevista.id}/pagar`, 200, paga),
    ]);
    await gotoApp(PATH);
    const linha = page.getByRole("row", { name: /Concreto usinado/ });
    await expect(linha).toContainText("Prevista");
    await page.evaluate(() => ((window as unknown as { __semReload: boolean }).__semReload = true));

    await linha.getByRole("button", { name: /Pagar/ }).click();
    const dialog = page.getByRole("alertdialog", { name: "Registrar pagamento" });
    await dialog.getByLabel("Data do pagamento").fill("");
    await dialog.getByRole("button", { name: "Confirmar pagamento" }).click();
    await expect(dialog.getByText("Informe a data do pagamento")).toBeVisible();

    await dialog.getByLabel("Data do pagamento").fill("2026-02-10");
    await dialog.getByRole("button", { name: "Confirmar pagamento" }).click();
    expect(await corpo(page, "POST", /\/pagar$/)).toEqual({ data_pagamento: "2026-02-10" });

    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toContainText("Paga");
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toContainText("10/02/2026");
    await expect(page.getByRole("row", { name: /Concreto usinado/ }).getByRole("button", { name: /Estornar/ })).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { __semReload?: boolean }).__semReload)).toBe(true);
  });

  test("axe: despesas, drawer de lançamento e categorias sem violação crítica", async ({ page, gotoApp }) => {
    await gotoApp(await despesasPath(page, gotoApp));
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toBeVisible();
    expect(await scan(page)).toEqual([]);

    await abrirLancamento(page);
    await page.getByLabel(/Parcelar/).click();
    expect(await scan(page)).toEqual([]);
    await page.keyboard.press("Escape");

    await gotoApp("/configuracoes/categorias");
    await expect(page.getByText("Materiais")).toBeVisible();
    expect(await scan(page)).toEqual([]);
  });
});

test.describe("financeiro · categorias", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("lista, cria e desativa categoria", async ({ page, gotoApp }) => {
    await stubFetch(page, []);
    await gotoApp("/configuracoes/categorias");
    await expect(page.getByText("Materiais")).toBeVisible();
    await expect(page.getByText("Mão de obra")).toBeVisible();

    await page.getByLabel("Nova categoria").fill("Equipamentos");
    await page.getByRole("button", { name: "Adicionar" }).click();
    expect(await corpo(page, "POST", /\/financeiro\/categorias$/)).toEqual({ nome: "Equipamentos" });

    await page.getByRole("listitem").filter({ hasText: "Materiais" }).getByRole("button", { name: "Desativar" }).click();
    expect(await corpo(page, "PATCH", /\/financeiro\/categorias\//)).toEqual({ ativa: false });
  });
});

/**
 * Estados e fluxos que o mock estático não produz. O `page.route` do Playwright não enxerga
 * requests atendidos pelo service worker do MSW; por isso o padrão `stubFetch` da S-F6
 * (financeiro-cronograma.spec.ts): `addInitScript` embrulhando `window.fetch`, que responde
 * só as rotas listadas e deixa o resto cair no MSW. Aqui cada stub tem `steps`: a n-ésima
 * chamada usa o n-ésimo passo (o último se repete), com `delayMs` opcional.
 */
interface Step {
  status: number;
  body: unknown;
  delayMs?: number;
}
interface Stub {
  method: string;
  path: string; // pathname exato após /api/v1
  steps: Step[];
}
const um = (method: string, path: string, status: number, body: unknown, delayMs?: number): Stub => ({
  method,
  path,
  steps: [{ status, body, delayMs }],
});

async function stubFetch(page: Page, stubs: Stub[]) {
  await page.addInitScript((lista) => {
    const original = window.fetch.bind(window);
    const contagem = new Map<number, number>();
    window.fetch = async (input, init) => {
      const url = new URL(
        typeof input === "string" ? input : input instanceof URL ? input.href : input.url,
        window.location.href,
      );
      const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
      const w = window as unknown as { __chamadas?: unknown[] };
      (w.__chamadas ??= []).push({
        method,
        path: url.pathname,
        search: url.search,
        body: typeof init?.body === "string" ? init.body : null,
      });
      const i = lista.findIndex((s) => s.method === method && url.pathname === `/api/v1${s.path}`);
      if (i < 0) return original(input, init);
      const n = contagem.get(i) ?? 0;
      contagem.set(i, n + 1);
      const passo = lista[i].steps[Math.min(n, lista[i].steps.length - 1)];
      if (passo.delayMs) await new Promise((r) => setTimeout(r, passo.delayMs));
      return new Response(JSON.stringify(passo.body), {
        status: passo.status,
        headers: { "Content-Type": passo.status >= 400 ? "application/problem+json" : "application/json" },
      });
    };
  }, stubs);
}

/**
 * O stub responde dentro da página, sem rede: `page.waitForRequest`/`page.on("request")` não
 * o enxergam. Por isso `stubFetch` grava TODA chamada a /api/v1 (stubada ou não) em
 * `window.__chamadas`, e os testes leem por aqui. Cada `gotoApp` recarrega a página e zera o
 * registro, então só contam as chamadas feitas depois da navegação.
 */
interface Chamada {
  method: string;
  path: string;
  search: string;
  body: string | null;
}
async function chamadas(page: Page, method: string, path: RegExp): Promise<Chamada[]> {
  const todas = await page.evaluate(
    () => (window as unknown as { __chamadas?: Chamada[] }).__chamadas ?? [],
  );
  return todas.filter((c) => c.method === method && path.test(c.path));
}
async function corpo(page: Page, method: string, path: RegExp): Promise<unknown> {
  await expect.poll(async () => (await chamadas(page, method, path)).length).toBe(1);
  const [c] = await chamadas(page, method, path);
  return JSON.parse(c.body ?? "null");
}

const PAGE = FINANCEIRO_EXEMPLOS.DespesaPage;
const OBRA = PAGE.items[0].obra_id;
const PATH = `/obras/${OBRA}/financeiro/despesas`;
const API_DESPESAS = `/obras/${OBRA}/despesas`;
const comoPapel = (role: string): Stub =>
  um("GET", "/auth/me", 200, { id: "u1", nome: "Teste", email: "teste@example.com", role });
const problema = { type: "about:blank", title: "Erro", status: 500, detail: "falhou" };

test.describe("financeiro · despesas: estados e fluxos via fetch stub", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("lançar despesa a faz aparecer na lista (POST devolve despesa nova; o GET seguinte a inclui)", async ({
    page,
    gotoApp,
  }) => {
    const nova = {
      ...PAGE.items[0],
      id: "01900000-0000-4000-8000-0000000000aa",
      descricao: "Reboco externo",
      valor: "800.00",
      vencimento: "2026-03-05",
    };
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          { status: 200, body: PAGE },
          { status: 200, body: { items: [nova, ...PAGE.items], next_cursor: null } },
        ],
      },
      um("POST", API_DESPESAS, 201, nova),
    ]);
    await gotoApp(PATH);
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Reboco externo/ })).toHaveCount(0);

    await abrirLancamento(page);
    await preencherBase(page);
    await page.getByLabel("Descrição").fill("Reboco externo");
    await page.getByLabel("Valor", { exact: true }).fill("80000");
    await page.getByLabel("Vencimento").fill("2026-03-05");
    await page.getByRole("button", { name: "Lançar despesa" }).last().click();

    await expect(page.getByRole("row", { name: /Reboco externo/ })).toContainText("R$ 800,00");
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toBeVisible();
  });

  test("loading mostra skeleton", async ({ page, gotoApp }) => {
    await stubFetch(page, [comoPapel("owner"), um("GET", API_DESPESAS, 200, PAGE, 4000)]);
    await gotoApp(PATH);
    await expect(page.locator('[data-slot="skeleton"]').first()).toBeVisible();
  });

  test("empty mostra CTA que abre o lançamento", async ({ page, gotoApp }) => {
    await stubFetch(page, [comoPapel("owner"), um("GET", API_DESPESAS, 200, { items: [], next_cursor: null })]);
    await gotoApp(PATH);
    await expect(page.getByText("Nenhuma despesa lançada")).toBeVisible();
    await page.getByRole("button", { name: "Lançar primeira despesa" }).click();
    await expect(page.getByRole("dialog", { name: "Lançar despesa" })).toBeVisible();
  });

  test("erro mostra retry e o retry recarrega a lista", async ({ page, gotoApp }) => {
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          // O QueryClient tenta 1 vez a mais (retry: 1): duas falhas antes do sucesso.
          { status: 500, body: problema },
          { status: 500, body: problema },
          { status: 200, body: PAGE },
        ],
      },
    ]);
    await gotoApp(PATH);
    await expect(page.getByText("Não foi possível carregar as despesas.")).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Tentar novamente" }).click();
    await expect(page.getByRole("row", { name: /Concreto usinado/ })).toBeVisible();
  });

  test("gestor lança e edita, mas não vê pagar/cancelar/estornar", async ({ page, gotoApp }) => {
    const paga = { ...PAGE.items[1], status: "paga", data_pagamento: "2026-02-25" };
    await stubFetch(page, [
      comoPapel("gestor"),
      um("GET", API_DESPESAS, 200, { items: [PAGE.items[0], paga], next_cursor: null }),
    ]);
    await gotoApp(PATH);
    const linha = page.getByRole("row", { name: /Concreto usinado/ });
    await expect(linha.getByRole("button", { name: /Editar/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Lançar despesa" })).toBeVisible();
    await expect(page.getByRole("button", { name: /^(Pagar|Cancelar|Estornar) / })).toHaveCount(0);
  });

  test("categoria inativa não é oferecida no lançamento (CA-F05.4)", async ({ page, gotoApp }) => {
    const [ativa, outra] = FINANCEIRO_EXEMPLOS["CategoriaOut[]"];
    await stubFetch(page, [
      comoPapel("owner"),
      um("GET", "/financeiro/categorias", 200, [
        ativa,
        { ...outra, id: "01900000-0000-4000-8000-0000000000bb", nome: "Legado inativa", ativa: false },
      ]),
    ]);
    await gotoApp(PATH);
    await abrirLancamento(page);
    await page.getByRole("combobox", { name: "Categoria" }).click();
    await expect(page.getByRole("option", { name: /Materiais/ })).toBeVisible();
    await expect(page.getByRole("option", { name: /Legado inativa/ })).toHaveCount(0);
    const lidas = await chamadas(page, "GET", /\/financeiro\/categorias$/);
    expect(lidas.length).toBeGreaterThan(0);
    expect(lidas.some((c) => c.search.includes("incluir_inativas"))).toBe(false);
  });

  test("obra sem fases: mensagem e lançamento bloqueado", async ({ page, gotoApp }) => {
    await stubFetch(page, [comoPapel("owner"), um("GET", `/obras/${OBRA}/fases`, 200, [])]);
    await gotoApp(PATH);
    await abrirLancamento(page);
    await expect(page.getByText(/aprove um orçamento para lançar despesas/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Lançar despesa" }).last()).toBeDisabled();
  });

  test("editar só a descrição envia PATCH apenas com {descricao}", async ({ page, gotoApp }) => {
    const d = PAGE.items[0];
    await stubFetch(page, [
      comoPapel("owner"),
      um("GET", API_DESPESAS, 200, PAGE),
      um("PATCH", `/financeiro/despesas/${d.id}`, 200, { ...d, descricao: "Concreto FCK 30" }),
    ]);
    await gotoApp(PATH);
    await page.getByRole("button", { name: "Editar Concreto usinado" }).click();
    const dialog = page.getByRole("dialog", { name: "Editar despesa" });
    await expect(dialog.getByLabel("Descrição")).toHaveValue("Concreto usinado");
    await dialog.getByLabel("Descrição").fill("Concreto FCK 30");
    await dialog.getByRole("button", { name: "Salvar alterações" }).click();
    expect(await corpo(page, "PATCH", /\/financeiro\/despesas\//)).toEqual({ descricao: "Concreto FCK 30" });
    await expect(dialog).toBeHidden();
  });

  test("editar sem mudar nada não envia PATCH", async ({ page, gotoApp }) => {
    await stubFetch(page, [comoPapel("owner"), um("GET", API_DESPESAS, 200, PAGE)]);
    await gotoApp(PATH);
    await page.getByRole("button", { name: "Editar Concreto usinado" }).click();
    const dialog = page.getByRole("dialog", { name: "Editar despesa" });
    await expect(dialog.getByLabel("Descrição")).toHaveValue("Concreto usinado");
    await dialog.getByRole("button", { name: "Salvar alterações" }).click();
    await expect(dialog).toBeHidden();
    expect(await chamadas(page, "PATCH", /./)).toEqual([]);
  });

  test("editar despesa de categoria inativa mantém a categoria atual e não a troca", async ({ page, gotoApp }) => {
    const d = { ...PAGE.items[0], categoria_id: "01900000-0000-4000-8000-0000000000bb", categoria_nome: "Legado" };
    await stubFetch(page, [
      comoPapel("owner"),
      um("GET", API_DESPESAS, 200, { items: [d], next_cursor: null }),
      // o servidor só devolve categorias ativas
      um("GET", "/financeiro/categorias", 200, FINANCEIRO_EXEMPLOS["CategoriaOut[]"]),
      um("PATCH", `/financeiro/despesas/${d.id}`, 200, { ...d, descricao: "Concreto B" }),
    ]);
    await gotoApp(PATH);
    await page.getByRole("button", { name: "Editar Concreto usinado" }).click();
    const dialog = page.getByRole("dialog", { name: "Editar despesa" });
    await expect(dialog.getByRole("combobox", { name: "Categoria" })).toContainText("Legado (inativa)");
    await dialog.getByLabel("Descrição").fill("Concreto B");
    await dialog.getByRole("button", { name: "Salvar alterações" }).click();
    expect(await corpo(page, "PATCH", /\/financeiro\/despesas\//)).toEqual({ descricao: "Concreto B" });
  });

  test("cancelar pela UI: confirma, chama DELETE e a linha vira cancelada", async ({ page, gotoApp }) => {
    const d = PAGE.items[0];
    const cancelada = { ...d, status: "cancelada" };
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          { status: 200, body: PAGE },
          { status: 200, body: { items: [cancelada, ...PAGE.items.slice(1)], next_cursor: null } },
        ],
      },
      um("DELETE", `/financeiro/despesas/${d.id}`, 200, cancelada),
    ]);
    await gotoApp(PATH);
    await page.getByRole("button", { name: "Cancelar Concreto usinado" }).click();
    const dialog = page.getByRole("alertdialog", { name: "Cancelar despesa?" });
    await dialog.getByRole("button", { name: "Cancelar despesa", exact: true }).click();
    await expect.poll(async () => (await chamadas(page, "DELETE", /\/financeiro\/despesas\//)).length).toBe(1);
    const linha = page.getByRole("row", { name: /Concreto usinado/ });
    await expect(linha).toContainText("Cancelada");
    await expect(linha.getByRole("button", { name: /^(Pagar|Cancelar|Editar) / })).toHaveCount(0);
  });

  test("estornar pela UI: confirma, chama POST /estornar e a linha volta a prevista", async ({ page, gotoApp }) => {
    const d = PAGE.items[0];
    const paga = { ...d, status: "paga", data_pagamento: "2026-02-10" };
    await stubFetch(page, [
      comoPapel("owner"),
      {
        method: "GET",
        path: API_DESPESAS,
        steps: [
          { status: 200, body: { items: [paga, ...PAGE.items.slice(1)], next_cursor: null } },
          { status: 200, body: PAGE },
        ],
      },
      um("POST", `/financeiro/despesas/${d.id}/estornar`, 200, d),
    ]);
    await gotoApp(PATH);
    const linha = page.getByRole("row", { name: /Concreto usinado/ });
    await expect(linha).toContainText("Paga");
    await page.getByRole("button", { name: "Estornar Concreto usinado" }).click();
    await page
      .getByRole("alertdialog", { name: "Estornar pagamento?" })
      .getByRole("button", { name: "Estornar", exact: true })
      .click();
    await expect.poll(async () => (await chamadas(page, "POST", /\/estornar$/)).length).toBe(1);
    await expect(linha).toContainText("Prevista");
    await expect(linha.getByRole("button", { name: /^Pagar / })).toBeVisible();
  });

  test("MoneyInput tecla a tecla: 150050 -> R$ 1.500,50; backspace -> R$ 150,05; envia 1500.50", async ({
    page,
    gotoApp,
  }) => {
    await stubFetch(page, [comoPapel("owner"), um("POST", API_DESPESAS, 201, PAGE.items[0])]);
    await gotoApp(PATH);
    await abrirLancamento(page);
    await preencherBase(page);
    await page.getByLabel("Vencimento").fill("2026-02-10");
    const valor = page.getByLabel("Valor", { exact: true });
    await valor.click();
    const esperado = ["R$ 0,01", "R$ 0,15", "R$ 1,50", "R$ 15,00", "R$ 150,05", "R$ 1.500,50"];
    // dígitos 1,5,0,0,5,0 -> 0,01 / 0,15 / 1,50 / 15,00 / 150,05 / 1.500,50
    for (const [i, tecla] of ["1", "5", "0", "0", "5", "0"].entries()) {
      await valor.press(tecla);
      await expect(valor).toHaveValue(esperado[i]);
    }
    await valor.press("Backspace");
    await expect(valor).toHaveValue("R$ 150,05");
    await valor.press("0");
    await expect(valor).toHaveValue("R$ 1.500,50");
    await page.getByRole("button", { name: "Lançar despesa" }).last().click();
    expect(await corpo(page, "POST", /\/obras\/[^/]+\/despesas$/)).toMatchObject({ valor: "1500.50" });
  });
});
