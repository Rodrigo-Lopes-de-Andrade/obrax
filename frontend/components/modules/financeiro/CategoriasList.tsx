"use client";

import * as React from "react";
import { Check, Loader2, Pencil, Plus, Tags, X } from "lucide-react";

import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import type { CategoriaOut } from "@/lib/api/types";
import {
  useCategorias,
  useCreateCategoria,
  useUpdateCategoria,
} from "@/lib/hooks/use-categorias";
import { useMe } from "@/lib/hooks/use-session";

// ESPEC §9 / E-10: só FIN mexe em categorias; os demais papéis leem.
const FIN_ROLES = new Set(["owner", "admin", "financeiro"]);

function CategoriaRow({ categoria, canEdit }: { categoria: CategoriaOut; canEdit: boolean }) {
  const update = useUpdateCategoria();
  const [editing, setEditing] = React.useState(false);
  const [nome, setNome] = React.useState(categoria.nome);

  function salvar(e: React.FormEvent) {
    e.preventDefault();
    const novo = nome.trim();
    if (!novo || novo === categoria.nome) return setEditing(false);
    // PATCH só com o campo alterado.
    update.mutate({ id: categoria.id, data: { nome: novo } }, { onSuccess: () => setEditing(false) });
  }

  return (
    <li className="flex items-center justify-between gap-3 px-4 py-3">
      {editing ? (
        <form onSubmit={salvar} className="flex flex-1 items-center gap-2">
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            aria-label={`Novo nome da categoria ${categoria.nome}`}
            maxLength={100}
            autoFocus
          />
          <Button type="submit" size="icon-sm" aria-label="Salvar nome" disabled={update.isPending}>
            {update.isPending ? <Loader2 className="animate-spin" /> : <Check />}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Cancelar edição"
            onClick={() => {
              setNome(categoria.nome);
              setEditing(false);
            }}
          >
            <X />
          </Button>
        </form>
      ) : (
        <>
          <span className="flex items-center gap-2 text-sm">
            {categoria.nome}
            {categoria.ativa ? null : <Badge variant="outline">Inativa</Badge>}
          </span>
          {canEdit ? (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Renomear ${categoria.nome}`}
                className="text-muted-foreground"
                onClick={() => setEditing(true)}
              >
                <Pencil />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={update.isPending}
                onClick={() => update.mutate({ id: categoria.id, data: { ativa: !categoria.ativa } })}
              >
                {categoria.ativa ? "Desativar" : "Reativar"}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </li>
  );
}

export function CategoriasList() {
  const [incluirInativas, setIncluirInativas] = React.useState(false);
  const { data, isLoading, isError, refetch } = useCategorias(incluirInativas);
  const create = useCreateCategoria();
  const { data: me } = useMe();
  const canEdit = me ? FIN_ROLES.has(me.role) : false;
  const [novoNome, setNovoNome] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  const items = data ?? [];

  function criar(e: React.FormEvent) {
    e.preventDefault();
    const nome = novoNome.trim();
    if (!nome) return;
    create.mutate({ nome }, { onSuccess: () => setNovoNome("") });
  }

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Categorias financeiras</h1>
        <p className="text-sm text-muted-foreground">
          Plano de contas das despesas. Categoria com despesa vinculada não é excluída, só desativada.
        </p>
      </div>

      {canEdit ? (
        <form onSubmit={criar} className="flex items-end gap-2">
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="nova-categoria">Nova categoria</Label>
            <Input
              id="nova-categoria"
              ref={inputRef}
              value={novoNome}
              onChange={(e) => setNovoNome(e.target.value)}
              placeholder="Equipamentos"
              maxLength={100}
            />
          </div>
          <Button type="submit" disabled={create.isPending || !novoNome.trim()}>
            {create.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
            Adicionar
          </Button>
        </form>
      ) : null}

      <div className="flex items-center gap-2">
        <Checkbox
          id="incluir-inativas"
          checked={incluirInativas}
          onCheckedChange={(c) => setIncluirInativas(c === true)}
        />
        <Label htmlFor="incluir-inativas">Mostrar inativas</Label>
      </div>

      {isError ? (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive"
        >
          <span>Não foi possível carregar as categorias.</span>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : isLoading ? (
        <div className="space-y-2" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Tags}
          title="Nenhuma categoria"
          description="Crie a primeira categoria para classificar as despesas."
          actionLabel={canEdit ? "Criar primeira categoria" : undefined}
          onAction={canEdit ? () => inputRef.current?.focus() : undefined}
        />
      ) : (
        <ul className="divide-y divide-border rounded-xl border border-border">
          {items.map((c) => (
            <CategoriaRow key={`${c.id}:${c.nome}:${c.ativa}`} categoria={c} canEdit={canEdit} />
          ))}
        </ul>
      )}
    </div>
  );
}
