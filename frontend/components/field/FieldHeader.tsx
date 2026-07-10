import { HardHat } from "lucide-react";

/** Barra superior do app de campo. O slot à direita recebe o SyncStatusBadge
 * (F7.6). Sticky para o indicador de sync ficar sempre visível. */
export function FieldHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-md items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary shadow-[0_4px_14px_rgba(255,107,107,0.35)]">
            <HardHat className="size-4.5 text-white" />
          </div>
          <span className="text-lg font-extrabold tracking-tight">
            Obra<span className="text-primary">x</span>{" "}
            <span className="text-sm font-semibold text-muted-foreground">Campo</span>
          </span>
        </div>
        <div id="field-header-slot" className="flex items-center gap-2" />
      </div>
    </header>
  );
}
