"use client";

import * as React from "react";
import { AlertTriangle, Download, FileArchive, Loader2, ShieldCheck, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { LgpdRequest, LgpdRequestType } from "@/lib/api/types";
import { useCriarPedidoLgpd, useLgpdRequests } from "@/lib/hooks/use-lgpd";
import { capture } from "@/lib/observability/analytics";

function fmtDataHora(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TIPO_LABEL: Record<LgpdRequestType, string> = {
  export: "Exportação",
  delete: "Eliminação",
};

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "concluido" ? "secondary" : status === "pendente" ? "outline" : "default";
  return <Badge variant={variant}>{status}</Badge>;
}

export function PrivacidadeView() {
  const { data, isLoading } = useLgpdRequests();
  const criar = useCriarPedidoLgpd();
  // Guarda o pedido de export recém-criado — o download_url só vem nesta resposta.
  const [ultimoExport, setUltimoExport] = React.useState<LgpdRequest | null>(null);
  const [confirmarDelete, setConfirmarDelete] = React.useState(false);

  function solicitar(tipo: LgpdRequestType) {
    criar.mutate(
      { request_type: tipo },
      {
        onSuccess: (req) => {
          if (tipo === "export") setUltimoExport(req);
          setConfirmarDelete(false);
          capture("lgpd_pedido_criado", { request_type: tipo });
        },
      },
    );
  }

  const requests = data?.items ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="flex items-start gap-3">
        <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
          <ShieldCheck className="size-5" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Privacidade & LGPD</h1>
          <p className="text-sm text-muted-foreground">
            Exporte ou solicite a eliminação dos seus dados pessoais (LGPD, art. 18).
          </p>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        {/* Exportação — disponibiliza um ZIP com todos os dados do titular. */}
        <section className="flex flex-col rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2">
            <FileArchive className="size-5 text-muted-foreground" />
            <h2 className="text-sm font-bold">Exportar meus dados</h2>
          </div>
          <p className="mt-1.5 flex-1 text-sm text-muted-foreground">
            Gera um arquivo ZIP com todos os dados pessoais que mantemos sobre você.
          </p>
          {ultimoExport?.download_url ? (
            <a
              href={ultimoExport.download_url}
              className="mt-3 inline-flex items-center justify-center gap-2 rounded-lg bg-success/10 px-3 py-2 text-sm font-medium text-success hover:bg-success/20"
            >
              <Download className="size-4" /> Baixar ZIP
            </a>
          ) : (
            <Button
              className="mt-3"
              onClick={() => solicitar("export")}
              disabled={criar.isPending}
            >
              {criar.isPending && criar.variables?.request_type === "export" ? (
                <Loader2 className="animate-spin" />
              ) : (
                <FileArchive />
              )}
              Solicitar exportação
            </Button>
          )}
        </section>

        {/* Eliminação — pedido irreversível, exige confirmação em dois passos. */}
        <section className="flex flex-col rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2">
            <Trash2 className="size-5 text-destructive" />
            <h2 className="text-sm font-bold">Eliminar meus dados</h2>
          </div>
          <p className="mt-1.5 flex-1 text-sm text-muted-foreground">
            Solicita a anonimização definitiva dos seus dados. Ação irreversível.
          </p>
          {confirmarDelete ? (
            <div className="mt-3 space-y-2">
              <p className="flex items-start gap-1.5 text-xs text-destructive">
                <AlertTriangle className="mt-0.5 size-3.5 flex-shrink-0" />
                Confirma? Seus dados serão anonimizados e não poderão ser recuperados.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setConfirmarDelete(false)}
                  disabled={criar.isPending}
                >
                  Cancelar
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => solicitar("delete")}
                  disabled={criar.isPending}
                >
                  {criar.isPending && criar.variables?.request_type === "delete" ? (
                    <Loader2 className="animate-spin" />
                  ) : null}
                  Confirmar
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="destructive"
              className="mt-3"
              onClick={() => setConfirmarDelete(true)}
              disabled={criar.isPending}
            >
              <Trash2 /> Solicitar eliminação
            </Button>
          )}
        </section>
      </div>

      <section>
        <h2 className="mb-2 text-sm font-bold">Histórico de solicitações</h2>
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          {isLoading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : requests.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">
              Nenhuma solicitação registrada.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Solicitado em</TableHead>
                  <TableHead>Expira em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">
                      {TIPO_LABEL[r.request_type]}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={r.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fmtDataHora(r.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fmtDataHora(r.expires_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </section>
    </div>
  );
}
