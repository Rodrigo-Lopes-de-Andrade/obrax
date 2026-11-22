"use client";

import * as React from "react";
import Decimal from "decimal.js";
import { useFormContext } from "react-hook-form";

import { Checkbox } from "@/components/ui/checkbox";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { formatDate } from "@/lib/format";
import { formatMoney, sum } from "@/lib/decimal";
import type { DespesaFormValues } from "./DespesaFormDrawer";

export const MIN_PARCELAS = 2;
export const MAX_PARCELAS = 120;

export interface ParcelaPrevia {
  numero: number;
  vencimento: string;
  valor: Decimal;
}

const pad2 = (n: number) => String(n).padStart(2, "0");

/** Soma `n` meses a uma data ISO, prendendo o dia ao último dia do mês de destino. */
export function addMonths(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const total = y * 12 + (m - 1) + n;
  const ny = Math.floor(total / 12);
  const nm = (total % 12) + 1;
  const last = new Date(Date.UTC(ny, nm, 0)).getUTCDate();
  return `${ny}-${pad2(nm)}-${pad2(Math.min(d, last))}`;
}

/**
 * Prévia das parcelas (RN-F08): `total / n` truncado em centavos, com o resíduo na
 * última — 1000,00 em 3 = 333,33 + 333,33 + 333,34. Tudo em Decimal.js, nunca Number.
 */
export function calcularParcelas(total: string, n: number, primeiroVencimento: string): ParcelaPrevia[] {
  const t = new Decimal(total);
  const base = t.div(n).toDecimalPlaces(2, Decimal.ROUND_DOWN);
  const ultima = t.minus(base.mul(n - 1));
  return Array.from({ length: n }, (_, i) => ({
    numero: i + 1,
    vencimento: addMonths(primeiroVencimento, i),
    valor: i === n - 1 ? ultima : base,
  }));
}

/** Valor menor que N centavos não se divide (E-11 → 422 no backend): recusado no client. */
export function valorMenorQueCentavos(total: string, n: number): boolean {
  return new Decimal(total).lt(new Decimal(n).div(100));
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Checkbox "Parcelar", nº de parcelas e prévia. O 1º vencimento é o campo `vencimento` do form. */
export function ParcelamentoFields() {
  const form = useFormContext<DespesaFormValues>();
  const parcelar = form.watch("parcelar");
  const valor = form.watch("valor");
  const numero = form.watch("numero_parcelas");
  const vencimento = form.watch("vencimento");

  const n = Number(numero);
  const nValido = Number.isInteger(n) && n >= MIN_PARCELAS && n <= MAX_PARCELAS;
  const pequeno = parcelar && valor !== "" && nValido && valorMenorQueCentavos(valor, n);
  const valido = parcelar && valor !== "" && nValido && !pequeno && ISO_DATE.test(vencimento);
  const parcelas = React.useMemo(
    () => (valido ? calcularParcelas(valor, n, vencimento) : []),
    [valido, valor, n, vencimento],
  );

  return (
    <div className="space-y-3 rounded-lg border border-border p-3">
      <FormField
        control={form.control}
        name="parcelar"
        render={({ field }) => (
          <FormItem className="flex flex-row items-center gap-2 space-y-0">
            <FormControl>
              <Checkbox
                checked={field.value}
                onCheckedChange={(c) => field.onChange(c === true)}
              />
            </FormControl>
            <FormLabel>Parcelar (vencimentos mensais)</FormLabel>
          </FormItem>
        )}
      />

      {parcelar ? (
        <>
          <FormField
            control={form.control}
            name="numero_parcelas"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Número de parcelas</FormLabel>
                <FormControl>
                  <Input type="number" inputMode="numeric" min={MIN_PARCELAS} max={MAX_PARCELAS} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {pequeno ? (
            <p role="alert" className="text-xs text-destructive">
              O valor total é menor que {n} centavos: não há como dividir em {n} parcelas.
            </p>
          ) : parcelas.length > 0 ? (
            <div aria-label="Prévia das parcelas" role="group" className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">
                Parcelas que serão geradas — confira antes de confirmar
              </p>
              <ul className="max-h-40 divide-y divide-border overflow-y-auto rounded-md border border-border text-sm">
                {parcelas.map((p) => (
                  <li key={p.numero} className="flex items-center justify-between px-3 py-1.5">
                    <span>
                      {p.numero}/{parcelas.length} · {formatDate(p.vencimento)}
                    </span>
                    <span className="tabular-nums">{formatMoney(p.valor)}</span>
                  </li>
                ))}
              </ul>
              <p className="flex justify-between px-1 text-xs text-muted-foreground">
                <span>Total</span>
                <span className="tabular-nums" data-testid="parcelas-total">
                  {formatMoney(sum(parcelas.map((p) => p.valor)))}
                </span>
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Informe valor, número de parcelas e o 1º vencimento para ver a prévia.
            </p>
          )}
        </>
      ) : null}
    </div>
  );
}
