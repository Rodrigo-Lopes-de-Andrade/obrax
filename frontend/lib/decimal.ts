import Decimal from "decimal.js";

type Money = Decimal.Value;

const brl = (value: Decimal, options: Intl.NumberFormatOptions) =>
  new Intl.NumberFormat("pt-BR", options).format(value.toNumber());

/** R$ 4.820.000,00 */
export function formatMoney(value: Money): string {
  return `R$ ${brl(new Decimal(value), { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** R$ 320.000 (sem casas decimais) */
export function formatMoneyRounded(value: Money): string {
  return `R$ ${brl(new Decimal(value), { maximumFractionDigits: 0 })}`;
}

/** R$ 4,82 mi */
export function formatMoneyMillions(value: Money): string {
  const millions = new Decimal(value).div(1_000_000);
  return `R$ ${millions.toFixed(2).replace(".", ",")} mi`;
}

/** { value: "R$ 4,82", unit: "mi" } — para compor com uma unidade menor no layout */
export function formatMoneyMillionsParts(value: Money): { value: string; unit: string } {
  const millions = new Decimal(value).div(1_000_000);
  return { value: `R$ ${millions.toFixed(2).replace(".", ",")}`, unit: "mi" };
}

export function formatNumber(value: Money): string {
  return new Intl.NumberFormat("pt-BR").format(new Decimal(value).toNumber());
}

export function formatPercent(value: Money, decimals = 1): string {
  return `${new Decimal(value).toFixed(decimals).replace(".", ",")}%`;
}

export function multiply(a: Money, b: Money): Decimal {
  return new Decimal(a).mul(b);
}

export function sum(values: Money[]): Decimal {
  return values.reduce<Decimal>((acc, v) => acc.plus(v), new Decimal(0));
}
