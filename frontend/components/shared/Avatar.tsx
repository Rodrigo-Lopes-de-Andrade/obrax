import { cn } from "@/lib/utils";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

/**
 * Avatar com iniciais (sem foto no MVP). Reutilizável em topbar e cards.
 * `variant="muted"` (padrão) para listas; `"gradient"` para o usuário logado.
 * Tamanho via `className` (size-*).
 */
export function Avatar({
  name,
  variant = "muted",
  className,
}: {
  name: string;
  variant?: "muted" | "gradient";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex size-8 shrink-0 select-none items-center justify-center rounded-full text-xs font-medium",
        variant === "gradient"
          ? "bg-gradient-to-br from-secondary to-[var(--chart-4)] font-bold text-white"
          : "bg-muted text-muted-foreground",
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
