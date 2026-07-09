"use client";

import * as React from "react";
import {
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  List,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDeleteDocumento, useDocumentos } from "@/lib/hooks/use-documentos";
import { cn } from "@/lib/utils";
import { CATEGORIAS_SUGERIDAS } from "./doc-meta";
import { DocumentosGallery } from "./DocumentosGallery";
import { DocumentosTable } from "./DocumentosTable";
import { UploadArea } from "./UploadArea";

const PAGE_SIZE = 50;
const TODAS = "todas";

export function DocumentosView({ obraId }: { obraId: string }) {
  const [view, setView] = React.useState<"list" | "gallery">("list");
  const [categoria, setCategoria] = React.useState<string>(TODAS);
  const [searchInput, setSearchInput] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [cursorStack, setCursorStack] = React.useState<string[]>([]);

  // Debounce da busca (evita um request por tecla).
  React.useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Volta à primeira página quando o filtro/busca muda.
  React.useEffect(() => {
    setCursorStack([]);
  }, [categoria, search]);

  const cursor = cursorStack.length ? cursorStack[cursorStack.length - 1] : null;
  const { data, isLoading, isFetching, isError } = useDocumentos(obraId, {
    categoria: categoria === TODAS ? null : categoria,
    search: search || null,
    cursor,
    limit: PAGE_SIZE,
  });
  const deleteDoc = useDeleteDocumento(obraId);

  const items = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const canPrev = cursorStack.length > 0;
  const deletingId = deleteDoc.isPending ? (deleteDoc.variables ?? null) : null;

  return (
    <div className="space-y-5">
      <UploadArea obraId={obraId} />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar por nome…"
            className="pl-9"
          />
        </div>
        <Select value={categoria} onValueChange={setCategoria}>
          <SelectTrigger size="sm" className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODAS}>Todas as categorias</SelectItem>
            {CATEGORIAS_SUGERIDAS.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="ml-auto flex items-center gap-1 rounded-lg border border-border p-0.5">
          <Button
            variant={view === "list" ? "secondary" : "ghost"}
            size="icon-sm"
            aria-label="Ver em lista"
            onClick={() => setView("list")}
          >
            <List />
          </Button>
          <Button
            variant={view === "gallery" ? "secondary" : "ghost"}
            size="icon-sm"
            aria-label="Ver em galeria"
            onClick={() => setView("gallery")}
          >
            <LayoutGrid />
          </Button>
        </div>
      </div>

      {isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Não foi possível carregar os documentos. Tente novamente.
        </div>
      ) : (
        <>
          <div
            className={cn(
              "transition-opacity",
              isFetching && !isLoading ? "opacity-60" : "opacity-100",
            )}
          >
            {view === "list" ? (
              <DocumentosTable
                docs={items}
                loading={isLoading}
                deletingId={deletingId}
                onDelete={(doc) => deleteDoc.mutate(doc.id)}
              />
            ) : (
              <DocumentosGallery
                docs={items}
                loading={isLoading}
                deletingId={deletingId}
                onDelete={(doc) => deleteDoc.mutate(doc.id)}
              />
            )}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Página {cursorStack.length + 1}
              {items.length > 0 ? ` · ${items.length} documentos` : ""}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCursorStack((s) => s.slice(0, -1))}
                disabled={!canPrev || isFetching}
              >
                <ChevronLeft />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  nextCursor && setCursorStack((s) => [...s, nextCursor])
                }
                disabled={!nextCursor || isFetching}
              >
                Próxima
                <ChevronRight />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
