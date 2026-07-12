"use client";

import * as React from "react";
import { Check, Loader2, Search } from "lucide-react";

import { Avatar } from "@/components/shared/Avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useAddMembro, useSearchUsuarios } from "@/lib/hooks/use-membros";
import type { Usuario } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { PAPEIS_SUGERIDOS } from "./papeis";

interface AddMembroDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  obraId: string;
  /** user_ids já na equipe (excluídos dos resultados). */
  existingUserIds: Set<string>;
}

export function AddMembroDrawer({
  open,
  onOpenChange,
  obraId,
  existingUserIds,
}: AddMembroDrawerProps) {
  const [searchInput, setSearchInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<Usuario | null>(null);
  const [papel, setPapel] = React.useState("");

  const addMembro = useAddMembro(obraId);

  React.useEffect(() => {
    if (open) {
      setSearchInput("");
      setSearch("");
      setSelected(null);
      setPapel("");
    }
  }, [open]);

  React.useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data, isLoading } = useSearchUsuarios(search);
  const resultados = (data?.items ?? []).filter(
    (u) => !existingUserIds.has(u.id),
  );

  function submit() {
    if (!selected || !papel) return;
    addMembro.mutate(
      { user_id: selected.id, papel },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Adicionar membro</SheetTitle>
          <SheetDescription>
            Busque um usuário da empresa e defina o papel na obra.
          </SheetDescription>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 px-4 pb-4">
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por nome ou e-mail…"
              className="pl-9"
            />
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-border">
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Buscando…
              </div>
            ) : resultados.length === 0 ? (
              <div className="py-10 text-center text-sm text-muted-foreground">
                Nenhum usuário disponível.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {resultados.map((u) => {
                  const active = selected?.id === u.id;
                  return (
                    <li key={u.id}>
                      <button
                        type="button"
                        onClick={() => setSelected(u)}
                        className={cn(
                          "flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors",
                          active ? "bg-primary/10" : "hover:bg-muted/60",
                        )}
                      >
                        <Avatar name={u.nome} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{u.nome}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {u.email}
                          </p>
                        </div>
                        {active ? (
                          <Check className="size-4 shrink-0 text-primary" />
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="space-y-1.5">
            <span className="text-sm font-medium">Papel</span>
            <Select value={papel} onValueChange={setPapel}>
              <SelectTrigger className="w-full" aria-label="Papel">
                <SelectValue placeholder="Selecione o papel" />
              </SelectTrigger>
              <SelectContent>
                {PAPEIS_SUGERIDOS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <SheetFooter>
          <Button
            onClick={submit}
            disabled={!selected || !papel || addMembro.isPending}
          >
            {addMembro.isPending ? <Loader2 className="animate-spin" /> : null}
            Adicionar
          </Button>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={addMembro.isPending}
          >
            Cancelar
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
