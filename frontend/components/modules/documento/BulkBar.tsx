"use client";

import { Eye, EyeOff, X } from "lucide-react";

import { Button } from "@/components/ui/button";

export function BulkBar({
  count,
  pending,
  onVisible,
  onInterno,
  onClear,
}: {
  count: number;
  pending: boolean;
  onVisible: () => void;
  onInterno: () => void;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-2.5 text-sm">
      <span className="font-medium">{count} selecionado(s)</span>
      <div className="ml-auto flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={onVisible} disabled={pending}>
          <Eye />
          Visível ao cliente
        </Button>
        <Button size="sm" variant="outline" onClick={onInterno} disabled={pending}>
          <EyeOff />
          Interno
        </Button>
        <Button size="sm" variant="ghost" onClick={onClear} aria-label="Limpar seleção">
          <X />
        </Button>
      </div>
    </div>
  );
}
