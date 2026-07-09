"use client";

import { Eye, EyeOff } from "lucide-react";

import { cn } from "@/lib/utils";

export function VisibilidadeToggle({
  visivel,
  onToggle,
  disabled = false,
}: {
  visivel: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={visivel}
      title={
        visivel
          ? "Visível ao cliente — clique para tornar interno"
          : "Interno — clique para tornar visível ao cliente"
      }
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs transition-colors disabled:opacity-50",
        visivel
          ? "border-primary/40 text-primary hover:bg-primary/10"
          : "border-border text-muted-foreground hover:bg-muted",
      )}
    >
      {visivel ? <Eye className="size-3.5" /> : <EyeOff className="size-3.5" />}
      {visivel ? "Cliente" : "Interno"}
    </button>
  );
}
