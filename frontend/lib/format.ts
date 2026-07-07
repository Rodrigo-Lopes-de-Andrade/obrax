/** Formata uma data ISO (YYYY-MM-DD) como dd/mm/aaaa, sem passar por Date
 * (evita deslocamento de fuso em datas sem horário). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  if (!y || !m || !d) return "—";
  return `${d}/${m}/${y}`;
}
