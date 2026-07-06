import { orcamentoInfo } from "@/lib/mock/dashboard-obra";

const FIELDS: { label: string; value: string; mono?: boolean }[] = [
  { label: "Cliente", value: orcamentoInfo.cliente },
  { label: "Obra", value: orcamentoInfo.obra },
  { label: "Responsável técnico", value: orcamentoInfo.responsavelTecnico },
  { label: "Regime", value: orcamentoInfo.regime },
  { label: "Data base", value: orcamentoInfo.dataBase, mono: true },
  { label: "BDI aplicado", value: `${orcamentoInfo.bdiPct.toFixed(1).replace(".", ",")}%`, mono: true },
];

export function DadosTab() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {FIELDS.map((field) => (
        <div key={field.label}>
          <label className="mb-1.5 block text-xs font-semibold text-muted-foreground">{field.label}</label>
          <div
            className={`rounded-lg border border-white/7 bg-card px-3.25 py-2.75 text-sm font-semibold ${
              field.mono ? "font-mono" : ""
            }`}
          >
            {field.value}
          </div>
        </div>
      ))}
    </div>
  );
}
