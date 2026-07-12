#!/usr/bin/env node
/**
 * Guarda de orçamento de bundle (F11.3). Lê o relatório do `next build` e reprova
 * se o "First Load JS" de alguma rota passar do teto. Serve de trava anti-regressão
 * em CI — hoje nenhuma dependência pesada entra no bundle; o objetivo é que continue
 * assim (uma lib pesada num route estoura o teto e falha o build).
 *
 * Fonte de verdade = a própria coluna "First Load JS" impressa pelo Next (métrica
 * canônica, já com dedupe de chunks). Uso:
 *   pnpm build:budget            # next build | tee .next/build-report.txt && este script
 *   node scripts/check-bundle-budget.mjs [caminho-do-relatorio]
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const REPORT = process.argv[2] ?? join(ROOT, ".next", "build-report.txt");

// Tetos em kB de First Load JS, com folga sobre os números atuais (maior ~203 kB)
// mas apertados o bastante p/ pegar a entrada de uma lib pesada num route.
const BUDGET = { route: 240, shared: 130 };

function toKb(value, unit) {
  const n = Number(value);
  return unit === "B" ? n / 1024 : unit === "MB" ? n * 1024 : n; // kB
}

let text;
try {
  text = readFileSync(REPORT, "utf8");
} catch {
  console.error(
    `✗ Relatório de build não encontrado em ${REPORT}.\n` +
      `  Rode: pnpm build:budget  (ou: next build | tee .next/build-report.txt)`,
  );
  process.exit(1);
}

// Linhas de rota do Next: "├ ○ /obras   4.54 kB   203 kB". Pega o caminho e o
// ÚLTIMO par número+unidade da linha = First Load JS. Rotas sem JS (0 B) são ignoradas.
const routeLine = /[│├└┌]\s*[○●ƒλ]\s+(\/\S*)\s+.*?([\d.]+)\s*(B|kB|MB)\s*$/;
const sharedLine = /First Load JS shared by all\s+([\d.]+)\s*(B|kB|MB)/;

const routes = [];
let shared = null;
for (const raw of text.split("\n")) {
  const line = raw.replace(/\[[0-9;]*m/g, ""); // tira ANSI, se houver
  const s = sharedLine.exec(line);
  if (s) shared = toKb(s[1], s[2]);
  const m = routeLine.exec(line);
  if (m) routes.push({ name: m[1], kb: toKb(m[2], m[3]) });
}

if (!routes.length) {
  console.error("✗ Não consegui extrair rotas do relatório de build.");
  process.exit(1);
}

const failures = [];
console.log("Bundle budget (First Load JS):\n");
for (const r of routes.sort((a, b) => b.kb - a.kb)) {
  const over = r.kb > BUDGET.route;
  if (over) failures.push(r);
  console.log(`  ${over ? "✗" : "✓"} ${r.kb.toFixed(0).padStart(4)} kB  ${r.name}`);
}
if (shared != null) {
  const over = shared > BUDGET.shared;
  if (over) failures.push({ name: "(shared baseline)", kb: shared });
  console.log(
    `\n  ${over ? "✗" : "✓"} ${shared.toFixed(0)} kB shared por todas (teto ${BUDGET.shared} kB)`,
  );
}

const worst = Math.max(...routes.map((r) => r.kb));
console.log(`\nMaior rota: ${worst.toFixed(0)} kB (teto ${BUDGET.route} kB). Rotas: ${routes.length}.`);

if (failures.length) {
  console.error(
    `\n✗ ${failures.length} item(ns) acima do orçamento:\n` +
      failures.map((f) => `   - ${f.name}: ${f.kb.toFixed(0)} kB`).join("\n"),
  );
  process.exit(1);
}
console.log("\n✓ Tudo dentro do orçamento.");
