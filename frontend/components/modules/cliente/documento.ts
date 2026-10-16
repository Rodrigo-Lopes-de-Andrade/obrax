import type { TipoPessoa } from "@/lib/api/types";

/** Espelho de backend/app/modules/gestao/clientes/validators.py — valida o dígito
 * verificador no client para o erro aparecer no campo, antes do 422. */
export const onlyDigits = (v: string) => v.replace(/\D/g, "");

function validCpf(d: string): boolean {
  if (d.length !== 11 || new Set(d).size === 1) return false;
  for (const len of [9, 10]) {
    let total = 0;
    for (let i = 0; i < len; i++) total += Number(d[i]) * (len + 1 - i);
    if (((total * 10) % 11) % 10 !== Number(d[len])) return false;
  }
  return true;
}

function validCnpj(d: string): boolean {
  if (d.length !== 14 || new Set(d).size === 1) return false;
  const first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  for (const [len, weights] of [
    [12, first],
    [13, [6, ...first]],
  ] as const) {
    let total = 0;
    for (let i = 0; i < len; i++) total += Number(d[i]) * weights[i];
    const rem = total % 11;
    if ((rem < 2 ? 0 : 11 - rem) !== Number(d[len])) return false;
  }
  return true;
}

export function isValidDocumento(tipo: TipoPessoa, documento: string): boolean {
  const d = onlyDigits(documento);
  return tipo === "PF" ? validCpf(d) : validCnpj(d);
}

/** 12345678909 → 123.456.789-09 · 11222333000181 → 11.222.333/0001-81 */
export function formatDocumento(documento: string): string {
  const d = onlyDigits(documento);
  if (d.length === 11) return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  if (d.length === 14) return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
  return documento;
}
