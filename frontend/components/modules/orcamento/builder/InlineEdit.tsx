"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface InlineEditProps {
  value: string;
  onCommit: (value: string) => void;
  disabled?: boolean;
  numeric?: boolean;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
}

/** Célula editável inline: mostra o valor; ao clicar vira input; commita no
 * blur/Enter (Esc cancela). Só dispara `onCommit` se o valor mudou. */
export function InlineEdit({
  value,
  onCommit,
  disabled,
  numeric,
  placeholder,
  className,
  inputClassName,
}: InlineEditProps) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(value);
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => setDraft(value), [value]);
  React.useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commit() {
    setEditing(false);
    const v = draft.trim();
    if (v !== value) onCommit(v);
  }

  if (disabled) {
    return (
      <span className={cn("block truncate", numeric && "text-right tabular-nums", className)}>
        {value || <span className="text-muted-foreground/60">{placeholder}</span>}
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
        {value || <span className="text-muted-foreground/50 italic">{placeholder ?? "—"}</span>}
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
          setDraft(value);
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
