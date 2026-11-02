"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface InlineEditProps {
  value: string;
  onCommit: (value: string) => void;
  disabled?: boolean;
  /** Valor no formato da API ("1234.5"); exibido/editado em pt-BR ("1.234,50"). */
  numeric?: boolean;
  /** Casas decimais mínimas na exibição numérica (ex.: 2 para preço). */
  decimals?: number;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
}

/** "1234.5" → "1.234,50" (exibição). Valor não numérico passa como está. */
function formatPtBr(value: string, decimals: number): string {
  const n = Number(value);
  if (value.trim() === "" || Number.isNaN(n)) return value;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: Math.max(decimals, 4),
  }).format(n);
}

/** Digitação pt-BR → formato da API: "1.234,56" / "1234,56" / "1234.56" → "1234.56".
 * Com vírgula, os pontos são separador de milhar. `null` = não é número. */
export function parsePtBr(input: string): string | null {
  const t = input.trim().replace(/\s/g, "");
  if (t === "") return "";
  const normalized = t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t;
  return /^-?\d+(\.\d+)?$/.test(normalized) ? normalized : null;
}

/** Célula editável inline: mostra o valor; ao clicar vira input; commita no
 * blur/Enter (Esc cancela). Só dispara `onCommit` se o valor mudou. */
export function InlineEdit({
  value,
  onCommit,
  disabled,
  numeric,
  decimals = 0,
  placeholder,
  className,
  inputClassName,
}: InlineEditProps) {
  // Numérico: edita com vírgula decimal (sem milhar, para não atrapalhar a digitação).
  const editValue = numeric ? value.replace(".", ",") : value;
  const shown = numeric ? formatPtBr(value, decimals) : value;
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(editValue);
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => setDraft(editValue), [editValue]);
  React.useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commit() {
    setEditing(false);
    if (numeric) {
      const v = parsePtBr(draft);
      if (v === null) {
        setDraft(editValue); // entrada inválida: volta ao valor anterior
        return;
      }
      if (v !== value) onCommit(v);
      return;
    }
    const v = draft.trim();
    if (v !== value) onCommit(v);
  }

  if (disabled) {
    return (
      <span className={cn("block truncate", numeric && "text-right tabular-nums", className)}>
        {shown || <span className="text-muted-foreground/60">{placeholder}</span>}
      </span>
    );
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        className={cn(
          "block w-full truncate rounded-md px-1.5 py-0.5 text-left hover:bg-white/5 hover:ring-1 hover:ring-border",
          numeric && "text-right tabular-nums",
          className,
        )}
      >
        {shown || <span className="text-muted-foreground/50 italic">{placeholder ?? "—"}</span>}
      </button>
    );
  }

  return (
    <input
      ref={inputRef}
      value={draft}
      inputMode={numeric ? "decimal" : undefined}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        } else if (e.key === "Escape") {
          setDraft(editValue);
          setEditing(false);
        }
      }}
      className={cn(
        "w-full rounded-md border border-primary/50 bg-background px-1.5 py-0.5 outline-none ring-2 ring-primary/20",
        numeric && "text-right tabular-nums",
        inputClassName,
      )}
    />
  );
}
