"use client";

import * as React from "react";
import { SlidersHorizontal } from "lucide-react";

import { Input } from "@/components/ui/input";
import type { OrcamentoItem, VersaoResumo } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useSetPrecificacao, useUpdateItem } from "@/lib/hooks/use-orcamentos";

interface Props {
  versaoId: string;
  versao: VersaoResumo;
  itens: OrcamentoItem[];
  locked: boolean;
}

const pctToFraction = (pct: number) => (pct / 100).toFixed(4);
const fractionToPct = (f: string) => Math.round(Number(f) * 10000) / 100;
/** Markup/taxa são validados em 0–100% (critério F6.2). */
const clampPct = (pct: number) => Math.min(100, Math.max(0, pct));

export function PrecificacaoTab({ versaoId, versao, itens, locked }: Props) {
  const setPrec = useSetPrecificacao(versaoId);
  const updateItem = useUpdateItem(versaoId);

  const [markup, setMarkup] = React.useState(fractionToPct(versao.markup_global));
  const [taxa, setTaxa] = React.useState(fractionToPct(versao.taxa_adm));
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const schedule = (m: number, t: number) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setPrec.mutate({ markup_global: pctToFraction(m), taxa_adm: pctToFraction(t) });
    }, 200);
  };

  const fases = itens.filter((i) => i.tipo === "F");

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-6 overflow-y-auto lg:grid-cols-[1fr_20rem]">
      {/* Sliders */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <SlidersHorizontal className="size-4" />
          Precificação — markup e taxa administrativa
        </div>

        <SliderField
          label="Markup global"
          hint="Aplicado onde não há override de fase/item"
          value={markup}
          max={100}
          disabled={locked}
          onChange={(v) => {
            setMarkup(v);
            schedule(v, taxa);
          }}
        />
        <SliderField
          label="Taxa administrativa"
          hint="Aplicada sobre o subtotal com markup (total)"
          value={taxa}
          max={30}
          disabled={locked}
          onChange={(v) => {
            setTaxa(v);
            schedule(markup, v);
          }}
        />

        <div className="space-y-2 border-t border-border pt-5">
          <div className="text-xs font-semibold tracking-wide text-muted-foreground/70 uppercase">
            Markup por fase (override)
          </div>
          <p className="text-xs text-muted-foreground">
            Deixe em branco para herdar o markup global. Sobrescreve toda a subárvore da fase.
          </p>
          <div className="divide-y divide-border/60 rounded-lg border border-border">
            {fases.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                Nenhuma fase ainda.
              </div>
            ) : (
              fases.map((f) => (
                <FaseOverrideRow
                  key={f.id}
                  descricao={f.descricao}
                  subtotal={f.subtotal}
                  override={f.markup_override}
                  globalPct={markup}
                  disabled={locked}
                  onCommit={(pct) =>
                    updateItem.mutate({
                      id: f.id,
                      patch: { markup_override: pct === null ? null : pctToFraction(pct) },
                    })
                  }
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <aside className="h-fit space-y-1 rounded-xl border border-border bg-card p-5">
        <div className="pb-2 text-sm font-semibold">Composição do preço</div>
        <BreakdownRow label="Custo direto" value={formatMoney(versao.custo_direto)} />
        <BreakdownRow label="Markup global" value={formatPercent(versao.markup_global)} muted />
        <BreakdownRow label="Taxa administrativa" value={formatPercent(versao.taxa_adm)} muted />
        <div className="my-2 border-t border-border" />
        <BreakdownRow label="Preço de venda" value={formatMoney(versao.preco_venda)} emphasis />
        <BreakdownRow label="Margem" value={formatPercent(versao.margem)} />
      </aside>
    </div>
  );
}

function SliderField({
  label,
  hint,
  value,
  max,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  max: number;
  disabled: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-sm font-medium">{label}</span>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </div>
        <span className="text-lg font-semibold tabular-nums text-primary">
          {value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        step={0.5}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary disabled:opacity-50"
      />
    </div>
  );
}

function FaseOverrideRow({
  descricao,
  subtotal,
  override,
  globalPct,
  disabled,
  onCommit,
}: {
  descricao: string;
  subtotal: string;
  override: string | null;
  globalPct: number;
  disabled: boolean;
  onCommit: (pct: number | null) => void;
}) {
  const [draft, setDraft] = React.useState(override != null ? String(fractionToPct(override)) : "");
  React.useEffect(() => {
    setDraft(override != null ? String(fractionToPct(override)) : "");
  }, [override]);

  const parsed = draft.trim() === "" ? null : Number(draft.trim().replace(",", "."));
  const invalid = parsed !== null && (Number.isNaN(parsed) || parsed < 0 || parsed > 100);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed === "") {
      if (override != null) onCommit(null);
      return;
    }
    const raw = Number(trimmed.replace(",", "."));
    if (Number.isNaN(raw)) {
      // Entrada inválida: reverte para o valor atual (herda global se null).
      setDraft(override != null ? String(fractionToPct(override)) : "");
      return;
    }
    const pct = clampPct(raw); // valida 0–100% (F6.2)
    setDraft(String(pct));
    if (pctToFraction(pct) !== override) onCommit(pct);
  };

  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2.5">
      <div className="min-w-0">
        <div className="truncate text-sm">{descricao}</div>
        <div className="text-xs text-muted-foreground tabular-nums">{formatMoney(subtotal)}</div>
      </div>
      <div className="flex items-center gap-1">
        <Input
          value={draft}
          disabled={disabled}
          inputMode="decimal"
          placeholder={`${globalPct}`}
          aria-invalid={invalid}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          className={cn(
            "h-8 w-20 text-right tabular-nums",
            invalid && "border-destructive focus-visible:ring-destructive/40",
          )}
          title={override == null ? `Herda o markup global (${globalPct}%)` : undefined}
        />
        <span className="text-sm text-muted-foreground">%</span>
      </div>
    </div>
  );
}

function BreakdownRow({
  label,
  value,
  muted,
  emphasis,
}: {
  label: string;
  value: string;
  muted?: boolean;
  emphasis?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className={cn("text-sm", muted ? "text-muted-foreground" : "")}>{label}</span>
      <span
        className={cn(
          "tabular-nums",
          emphasis ? "text-lg font-semibold text-primary" : "text-sm font-medium",
        )}
      >
        {value}
      </span>
    </div>
  );
}
