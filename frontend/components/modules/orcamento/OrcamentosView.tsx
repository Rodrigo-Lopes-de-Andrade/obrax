"use client";

import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { FilePlus2, Loader2, Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Orcamento, OrcamentoStatus } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { useObras } from "@/lib/hooks/use-obras";
import { useDeleteOrcamento, useOrcamentos } from "@/lib/hooks/use-orcamentos";
// Code-split (F11.3): drawer de criação carrega sob demanda, fora do bundle inicial.
const CreateOrcamentoDrawer = dynamic(() =>
  import("./CreateOrcamentoDrawer").then((m) => m.CreateOrcamentoDrawer),
);
import { ORCAMENTO_STATUS_OPTIONS, OrcamentoStatusBadge } from "./status";

export function OrcamentosView() {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [statusFilter, setStatusFilter] = React.useState<OrcamentoStatus | "todos">("todos");

  const { data, isLoading } = useOrcamentos({ limit: 100 });
  const { data: obrasPage } = useObras({ limit: 100 });
  const deleteOrcamento = useDeleteOrcamento();

  const obraLabel = React.useMemo(() => {
    const map = new Map((obrasPage?.items ?? []).map((o) => [o.id, `${o.codigo} · ${o.nome}`]));
    return (id: string) => map.get(id) ?? "—";
  }, [obrasPage]);

  const rows = (data?.items ?? []).filter(
    (o) => statusFilter === "todos" || o.status === statusFilter,
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Orçamentos</h1>
          <p className="text-sm text-muted-foreground">
            Estrutura analítica (EAP), precificação e aprovação por obra.
          </p>
        </div>
        <Button onClick={() => setDrawerOpen(true)}>
          <FilePlus2 />
          Novo orçamento
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as OrcamentoStatus | "todos")}
        >
          <SelectTrigger size="sm" className="w-52" aria-label="Filtrar por status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {ORCAMENTO_STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Título</TableHead>
              <TableHead>Obra</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-center">Rev.</TableHead>
              <TableHead>Criado em</TableHead>
              <TableHead className="w-0" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={`sk-${i}`} className="hover:bg-transparent">
                  {Array.from({ length: 6 }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full max-w-28" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell
                  colSpan={6}
                  className="h-24 text-center text-sm text-muted-foreground"
                >
                  Nenhum orçamento ainda. Crie o primeiro.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((o) => (
                <OrcamentoRow
                  key={o.id}
                  orcamento={o}
                  obraLabel={obraLabel(o.obra_id)}
                  onDelete={() => deleteOrcamento.mutate(o.id)}
                  deleting={deleteOrcamento.isPending && deleteOrcamento.variables === o.id}
                />
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <CreateOrcamentoDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </div>
  );
}

function OrcamentoRow({
  orcamento,
  obraLabel,
  onDelete,
  deleting,
}: {
  orcamento: Orcamento;
  obraLabel: string;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <TableRow>
      <TableCell>
        <Link
          href={`/orcamentos/${orcamento.id}/edit`}
          className="font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
        >
          {orcamento.titulo}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground">{obraLabel}</TableCell>
      <TableCell>
        <OrcamentoStatusBadge status={orcamento.status} />
      </TableCell>
      <TableCell className="text-center tabular-nums text-muted-foreground">
        {orcamento.versao_atual}
      </TableCell>
      <TableCell className="text-muted-foreground tabular-nums">
        {formatDate(orcamento.created_at)}
      </TableCell>
      <TableCell className="w-0">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Excluir orçamento"
              className="text-muted-foreground hover:text-destructive"
              disabled={deleting}
            >
              {deleting ? <Loader2 className="animate-spin" /> : <Trash2 />}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Excluir orçamento?</AlertDialogTitle>
              <AlertDialogDescription>
                O orçamento{" "}
                <span className="font-medium text-foreground">{orcamento.titulo}</span> e
                todas as suas versões serão removidos.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction
                onClick={onDelete}
                className="bg-destructive/10 text-destructive hover:bg-destructive/20"
              >
                Excluir
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </TableCell>
    </TableRow>
  );
}
