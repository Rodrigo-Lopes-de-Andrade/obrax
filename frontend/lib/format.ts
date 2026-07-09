/** Formata uma data ISO (YYYY-MM-DD) como dd/mm/aaaa, sem passar por Date
 * (evita deslocamento de fuso em datas sem horário). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  if (!y || !m || !d) return "—";
  return `${d}/${m}/${y}`;
}

/** Tamanho de arquivo legível (KB/MB), base 1024. */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/** Formata um Decimal (string do backend) como moeda pt-BR: "R$ 12.345,67".
 * Só para exibição — cálculos usam Decimal.js/backend (nunca Number). */
export function formatMoney(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Versão compacta para KPIs grandes: "R$ 1,2 mi", "R$ 340 mil". */
export function formatMoneyCompact(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000)
    return `R$ ${(n / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} mi`;
  if (Math.abs(n) >= 1_000)
    return `R$ ${(n / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  return formatMoney(n);
}

/** Fração (string "0.2500") como percentual pt-BR: "25,00%". */
export function formatPercent(
  fraction: string | number | null | undefined,
  digits = 2,
): string {
  if (fraction == null || fraction === "") return "—";
  const n = typeof fraction === "number" ? fraction : Number(fraction);
  if (Number.isNaN(n)) return "—";
  return `${(n * 100).toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}
