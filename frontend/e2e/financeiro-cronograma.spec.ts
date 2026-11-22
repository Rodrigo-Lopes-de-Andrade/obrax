import AxeBuilder from "@axe-core/playwright";

import { FINANCEIRO_EXEMPLOS } from "../lib/mock/db";
import { expect, test, type Page } from "./fixtures";

/**
 * Tela de cronograma (S-F6, US-F01/US-F02) contra o mock MSW (FINANCEIRO_EXEMPLOS):
 * Fundação 100.000,00 (50/30/20%) e Estrutura 50.000,00 (20/40/40%), 3 períodos,
 * desbloqueado, usuário mock com papel `owner`.
 *
 * Os estados que o mock não produz (bloqueado, gestor, 404, sem orçamento aprovado)
 * ficam no describe "estados via fetch stub", no fim do arquivo.
 *
 * A allowlist de contraste das cores de marca replica a de a11y.spec.ts: um
 * AxeBuilder sem ela reprova nas violações de #ff6b6b/#845ef7 já toleradas.
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

async function varrerAxe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return results.violations
    .filter((v) => v.impact === "critical" || v.impact === "serious")
    .filter((v) => !isBrandAccentContrast(v));
}

async function abrirCronograma(page: Page, gotoApp: (path: string) => Promise<void>) {
  await gotoApp("/obras");
  // `.first().getAttribute()` espera a lista carregar (o evaluateAll não espera).
  const href = await page.locator('table a[href^="/obras/"]').first().getAttribute("href");
  expect(href, "nenhuma obra na lista do mock").toBeTruthy();
  const obraId = href!.split("/")[2];
  await gotoApp(`/obras/${obraId}/cronograma`);
  await expect(page.getByRole("table")).toBeVisible();
}

const celula = (page: Page, fase: string, periodo: number) =>
  page.getByRole("textbox", { name: new RegExp(`fase ${fase} .* no período ${periodo}$`) });

test.describe("cronograma", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("grade com fases nas linhas, períodos nas colunas e totais", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    await expect(page.getByRole("columnheader", { name: /Período 1/ })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Período 3/ })).toBeVisible();
    await expect(page.getByRole("rowheader", { name: /Fundação/ })).toBeVisible();
    await expect(page.getByRole("rowheader", { name: /Estrutura/ })).toBeVisible();
    // Total do período 1: 50.000 + 10.000. Total geral: 150.000.
    const rodape = page.locator("tfoot tr").first().getByRole("cell");
    await expect(rodape.nth(0)).toHaveText("R$ 60.000,00");
    await expect(rodape.nth(1)).toHaveText("R$ 50.000,00");
    await expect(rodape.nth(2)).toHaveText("R$ 40.000,00");
    await expect(rodape.nth(3)).toContainText("R$ 150.000,00");
    await expect(page.getByRole("button", { name: "Salvar cronograma" })).toBeDisabled();
  });

  test("editar célula recalcula totais na hora (positivo) e libera o salvar", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    // Fundação: 50/30/20 -> 40/30/30 (continua 100%).
    // Antes: total do período 1 = 50.000 + 10.000 = 60.000; período 3 = 20.000 + 20.000 = 40.000.
    const totais = page.locator("tfoot tr").first().getByRole("cell");
    await expect(totais.nth(0)).toHaveText("R$ 60.000,00");
    await expect(totais.nth(2)).toHaveText("R$ 40.000,00");
    await celula(page, "01", 1).fill("40");
    await celula(page, "01", 3).fill("30");
    // Depois: período 1 = 40.000 + 10.000 = 50.000; período 3 = 30.000 + 20.000 = 50.000.
    await expect(totais.nth(0)).toHaveText("R$ 50.000,00");
    await expect(totais.nth(0)).not.toHaveText("R$ 60.000,00");
    await expect(totais.nth(2)).toHaveText("R$ 50.000,00");
    // O R$ da própria célula editada também recalcula (40% de 100.000).
    await expect(page.getByRole("row", { name: /Fundação/ }).getByRole("cell").first()).toContainText("R$ 40.000,00");
    await expect(page.getByText(/não soma 100%/i)).toHaveCount(0);
    const salvar = page.getByRole("button", { name: "Salvar cronograma" });
    await expect(salvar).toBeEnabled();
    await salvar.click();
    await expect(page.getByText("Cronograma salvo")).toBeVisible();
  });

  test("0,9999 aparece como 'não soma 100%' com texto e bloqueia o salvar com o motivo", async ({
    page,
    gotoApp,
  }) => {
    await abrirCronograma(page, gotoApp);
    await celula(page, "01", 3).fill("19,99"); // 0.5 + 0.3 + 0.1999 = 0.9999
    await expect(page.getByRole("cell", { name: /Não soma 100%: faltam 0,01%/ })).toBeVisible();
    const salvar = page.getByRole("button", { name: "Salvar cronograma" });
    await expect(salvar).toBeDisabled();
    await expect(page.locator("#cronograma-motivo")).toContainText("Fase 01 Fundação soma 99,99%");
    await expect(page.locator("#cronograma-motivo")).toContainText("Não é possível salvar");
  });

  test("navegação por teclado: Tab entre células e setas verticais", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    await celula(page, "01", 1).focus();
    await page.keyboard.press("Tab");
    await expect(celula(page, "01", 2)).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(celula(page, "02", 2)).toBeFocused();
    await page.keyboard.press("ArrowUp");
    await expect(celula(page, "01", 2)).toBeFocused();
  });

  test("axe: sem violação crítica/séria (mesma allowlist de marca do a11y.spec)", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    const serious = await varrerAxe(page);
    expect(serious, serious.map((v) => `${v.id}: ${v.help}`).join("\n")).toEqual([]);
  });

  test("axe: com fase inválida destacada (não soma 100%)", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    await celula(page, "01", 3).fill("19,99");
    await expect(page.locator('[id^="cron-msg-"]')).toContainText("Não soma 100%: faltam 0,01%");
    const serious = await varrerAxe(page);
    expect(serious, serious.map((v) => `${v.id}: ${v.help}`).join("\n")).toEqual([]);
  });

  test("setas ←/→ andam entre períodos e células apontam a mensagem da fase", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    await celula(page, "01", 3).fill("19,99");
    // A mensagem da célula (span#cron-msg-…) é única; a da toolbar fica em #cronograma-motivo.
    const msg = page.locator('[id^="cron-msg-"]');
    await expect(msg).toHaveCount(1);
    await expect(msg).toContainText("Não soma 100%: faltam 0,01%");
    const id = await msg.getAttribute("id");
    await expect(celula(page, "01", 1)).toHaveAttribute("aria-describedby", id!);
    await expect(celula(page, "02", 1)).not.toHaveAttribute("aria-describedby", /.+/);
    await celula(page, "01", 1).focus(); // foco seleciona tudo: o cursor está na borda
    await page.keyboard.press("ArrowRight");
    await expect(celula(page, "01", 2)).toBeFocused();
    await page.keyboard.press("ArrowLeft");
    await expect(celula(page, "01", 1)).toBeFocused();
  });

  test("célula não editada mostra o valor_planejado do servidor", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    const linha = page.getByRole("row", { name: /Estrutura/ });
    await expect(linha.getByRole("cell").nth(0)).toContainText("R$ 10.000,00");
    await expect(linha.getByRole("cell").nth(3)).toContainText("R$ 50.000,00"); // total da fase
  });

  test("PUT envia FRAÇÃO com 4 casas (não percentual) e cada fase soma 1", async ({ page, gotoApp }) => {
    const putPath = `/cronograma/${GRADE.cronograma.id}/alocacoes`;
    await stubFetch(page, [
      getGrade(GRADE),
      comoPapel("owner"),
      { method: "PUT", path: putPath, status: 200, body: GRADE },
    ]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await celula(page, "01", 1).fill("40");
    await celula(page, "01", 3).fill("30");
    await page.getByRole("button", { name: "Salvar cronograma" }).click();
    await expect(page.getByText("Cronograma salvo")).toBeVisible();
    // Request stubado não passa pela rede: lê o corpo gravado pelo stub.
    const bruto = await page.evaluate(
      (k) => (window as unknown as { __corpos: Record<string, string> }).__corpos[k],
      `PUT /api/v1${putPath}`,
    );
    const corpo = JSON.parse(bruto) as { alocacoes: { obra_fase_id: string; periodo_id: string; percentual_planejado: string }[] };
    expect(corpo.alocacoes).toHaveLength(6); // PUT substitui o conjunto inteiro
    for (const a of corpo.alocacoes) expect(a.percentual_planejado).toMatch(/^[01]\.\d{4}$/);
    const porFase = (faseId: string) =>
      GRADE.periodos.map((p) => corpo.alocacoes.find((a) => a.obra_fase_id === faseId && a.periodo_id === p.id)?.percentual_planejado);
    const [fundacao, estrutura] = GRADE.fases.map((f) => porFase(f.obra_fase_id));
    expect(fundacao).toEqual(["0.4000", "0.3000", "0.3000"]);
    expect(estrutura).toEqual(["0.2000", "0.4000", "0.4000"]);
    // Soma exata 1.0000 por fase, em inteiros (sem float).
    for (const f of [fundacao, estrutura]) {
      const total = f.reduce((acc, v) => acc + BigInt((v ?? "0").replace(".", "")), BigInt(0));
      expect(total).toBe(BigInt(10000));
    }
  });

  test("célula não editada mostra o valor_planejado do servidor (difere do recálculo)", async ({ page, gotoApp }) => {
    // Orçado 100,01 em 33,33/33,33/33,34%: recalcular daria 33,33 + 33,33 + 33,34 = 100,00.
    // O servidor fecha 100,01 (33,33 + 33,34 + 33,34) e a tela tem de mostrar isso.
    const [p1, p2, p3] = GRADE.periodos;
    const fase = {
      obra_fase_id: GRADE.fases[0].obra_fase_id,
      codigo: "01",
      descricao: "Fundação",
      valor_orcado: "100.01",
      alocacoes: [
        { periodo_id: p1.id, percentual_planejado: "0.3333", valor_planejado: "33.33" },
        { periodo_id: p2.id, percentual_planejado: "0.3333", valor_planejado: "33.34" },
        { periodo_id: p3.id, percentual_planejado: "0.3334", valor_planejado: "33.34" },
      ],
    };
    await stubFetch(page, [getGrade({ ...GRADE, fases: [fase] }), comoPapel("owner")]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    const cells = page.getByRole("row", { name: /Fundação/ }).getByRole("cell");
    await expect(cells.nth(1)).toContainText("R$ 33,34");
    await expect(cells.nth(1)).not.toContainText("R$ 33,33");
    await expect(cells.nth(3)).toContainText("R$ 100,01");
    await expect(cells.nth(3)).toContainText("100,00%");
  });

  test("soma 1,0001 aparece como 'excede em' com salvar desabilitado e motivo", async ({ page, gotoApp }) => {
    await abrirCronograma(page, gotoApp);
    await celula(page, "01", 3).fill("20,01");
    await expect(page.locator('[id^="cron-msg-"]')).toContainText("Não soma 100%: excede em 0,01%");
    await expect(page.getByRole("button", { name: "Salvar cronograma" })).toBeDisabled();
    await expect(page.locator("#cronograma-motivo")).toContainText("Fase 01 Fundação soma 100,01%");
  });

  for (const invalido of ["abc", "100,5", "-5"]) {
    test(`célula inválida "${invalido}" bloqueia o salvar com o motivo`, async ({ page, gotoApp }) => {
      await abrirCronograma(page, gotoApp);
      await celula(page, "01", 3).fill(invalido);
      await expect(celula(page, "01", 3)).toHaveAttribute("aria-invalid", "true");
      await expect(page.getByRole("button", { name: "Salvar cronograma" })).toBeDisabled();
      await expect(page.locator("#cronograma-motivo")).toContainText("Fase 01 Fundação, período 3: informe um percentual");
    });
  }
});

/**
 * Estados que o mock MSW não produz. O `page.route` do Playwright NÃO enxerga requests
 * atendidos pelo service worker do MSW, e bloquear o worker travaria o app (providers.tsx
 * espera `worker.start()`, que rejeita sem o script). Saída: um `addInitScript` que embrulha
 * `window.fetch` e responde só as rotas listadas; o resto cai no fetch original (e no MSW).
 * O client (lib/api/client.ts) chama `fetch` global a cada request, então o stub o alcança.
 * Os payloads reaproveitam FINANCEIRO_EXEMPLOS (tipos de lib/api/types.ts).
 */
interface Stub {
  method: string;
  path: string; // pathname exato após /api/v1
  status: number;
  body: unknown;
  /** Resposta das chamadas seguintes à primeira (ex.: 500 e depois 200). */
  depois?: { status: number; body: unknown };
  /** Com `true`, `depois` só vale após `window.__stubCurado = true` (não conta chamadas). */
  porFlag?: boolean;
}

async function stubFetch(page: Page, stubs: Stub[]) {
  await page.addInitScript((lista) => {
    const chamadas = new Map<unknown, number>();
    const original = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, window.location.href);
      const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
      const hit = lista.find((s) => s.method === method && url.pathname === `/api/v1${s.path}`);
      if (!hit) return original(input, init);
      const w = window as unknown as { __corpos?: Record<string, string> };
      (w.__corpos ??= {})[`${method} ${url.pathname}`] = typeof init?.body === "string" ? init.body : "";
      const n = chamadas.get(hit) ?? 0;
      chamadas.set(hit, n + 1);
      const virou = hit.porFlag ? (window as unknown as { __stubCurado?: boolean }).__stubCurado === true : n > 0;
      const r = virou && hit.depois ? hit.depois : hit;
      return new Response(JSON.stringify(r.body), {
        status: r.status,
        headers: { "Content-Type": r.status >= 400 ? "application/problem+json" : "application/json" },
      });
    };
  }, stubs);
}

const GRADE = FINANCEIRO_EXEMPLOS.CronogramaGradeOut;
const OBRA = GRADE.cronograma.obra_id;
const gradeBloqueada = {
  ...GRADE,
  cronograma: { ...GRADE.cronograma, bloqueado_em: "2026-02-10T12:00:00Z" },
};
const semCronograma: Stub = {
  method: "GET",
  path: `/obras/${OBRA}/cronograma`,
  status: 404,
  body: { type: "about:blank", title: "Not Found", status: 404, detail: "Obra sem cronograma" },
};
const comoPapel = (role: string): Stub => ({
  method: "GET",
  path: "/auth/me",
  status: 200,
  body: { id: "u1", nome: "Teste", email: "teste@example.com", role },
});
const getGrade = (g: unknown): Stub => ({ method: "GET", path: `/obras/${OBRA}/cronograma`, status: 200, body: g });

test.describe("cronograma: estados via fetch stub", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("bloqueado abre em leitura com aviso explicando por quê", async ({ page, gotoApp }) => {
    await stubFetch(page, [getGrade(gradeBloqueada), comoPapel("owner")]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await expect(page.getByRole("status").filter({ hasText: "Cronograma bloqueado para edição" })).toContainText(
      "medição aprovada",
    );
    await expect(celula(page, "01", 1)).toHaveAttribute("readonly", "");
    await expect(page.getByRole("button", { name: "Salvar cronograma" })).toHaveCount(0);
  });

  test("gestor só lê: aviso de papel e células readonly", async ({ page, gotoApp }) => {
    await stubFetch(page, [getGrade(GRADE), comoPapel("gestor")]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await expect(page.getByText(/apenas consultar o cronograma/)).toBeVisible();
    await expect(celula(page, "01", 1)).toHaveAttribute("readonly", "");
    await expect(page.getByRole("button", { name: "Salvar cronograma" })).toHaveCount(0);
  });

  test("404 sem orçamento aprovado: o POST recusa (422) e a tela mostra a mensagem com CTA", async ({
    page,
    gotoApp,
  }) => {
    const falta = "Obra sem orçamento aprovado: aprove um orçamento antes de gerar o cronograma.";
    await stubFetch(page, [
      semCronograma,
      comoPapel("owner"),
      { method: "POST", path: `/obras/${OBRA}/cronograma`, status: 422, body: { title: "Unprocessable", status: 422, detail: falta } },
    ]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await page.getByLabel("Data de início").fill("2026-01-01");
    await page.getByRole("button", { name: "Gerar cronograma" }).click();
    await expect(page.getByRole("alert").filter({ hasText: falta })).toBeVisible();
    await page.getByRole("button", { name: "Ir para os orçamentos" }).click();
    await expect(page).toHaveURL(/\/orcamentos$/);
  });

  test("404 mostra o formulário e gera o cronograma", async ({ page, gotoApp }) => {
    await stubFetch(page, [
      semCronograma,
      comoPapel("owner"),
      { method: "POST", path: `/obras/${OBRA}/cronograma`, status: 201, body: GRADE },
    ]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await expect(page.getByText("Esta obra ainda não tem cronograma")).toBeVisible();
    await page.getByLabel("Data de início").fill("2026-01-01");
    await page.getByRole("button", { name: "Gerar cronograma" }).click();
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByRole("rowheader", { name: /Fundação/ })).toBeVisible();
  });

  test("404 como gestor: sem botão de gerar", async ({ page, gotoApp }) => {
    await stubFetch(page, [semCronograma, comoPapel("gestor")]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await expect(page.getByText(/A geração é de owner, admin e financeiro/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Gerar cronograma" })).toHaveCount(0);
  });

  test("erro que não é 404 mostra erro com 'Tentar novamente'", async ({ page, gotoApp }) => {
    await stubFetch(page, [
      {
        method: "GET",
        path: `/obras/${OBRA}/cronograma`,
        status: 500,
        body: { title: "Erro", status: 500, detail: "Falha no servidor" },
        depois: { status: 200, body: GRADE },
        porFlag: true,
      },
      comoPapel("owner"),
    ]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    // Os retries automáticos do hook esgotam (~3 s) e só então aparece o erro.
    await expect(page.getByRole("alert").filter({ hasText: "Falha no servidor" })).toBeVisible({ timeout: 15_000 });
    await page.evaluate(() => {
      (window as unknown as { __stubCurado?: boolean }).__stubCurado = true;
    });
    await page.getByRole("button", { name: "Tentar novamente" }).click();
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("PUT 409 (bloqueou no meio da edição): mensagem e grade em leitura", async ({ page, gotoApp }) => {
    await stubFetch(page, [
      { method: "GET", path: `/obras/${OBRA}/cronograma`, status: 200, body: GRADE, depois: { status: 200, body: gradeBloqueada } },
      comoPapel("owner"),
      {
        method: "PUT",
        path: `/cronograma/${GRADE.cronograma.id}/alocacoes`,
        status: 409,
        body: { title: "Conflict", status: 409, detail: "Cronograma bloqueado: há medição aprovada." },
      },
    ]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await celula(page, "01", 1).fill("40");
    await celula(page, "01", 3).fill("30");
    await page.getByRole("button", { name: "Salvar cronograma" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Cronograma bloqueado: há medição aprovada." })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Cronograma bloqueado para edição" })).toBeVisible();
    await expect(celula(page, "01", 1)).toHaveAttribute("readonly", "");
  });

  test("axe no estado bloqueado", async ({ page, gotoApp }) => {
    await stubFetch(page, [getGrade(gradeBloqueada), comoPapel("owner")]);
    await gotoApp(`/obras/${OBRA}/cronograma`);
    await expect(page.getByRole("table")).toBeVisible();
    const serious = await varrerAxe(page);
    expect(serious, serious.map((v) => `${v.id}: ${v.help}`).join("\n")).toEqual([]);
  });
});
