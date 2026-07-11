"use client";

import * as React from "react";
import { Bot, Loader2, RotateCcw, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
import type { AgentInteraction, AgentInteractionStatus } from "@/lib/api/types";
import { useObras } from "@/lib/hooks/use-obras";
import { useInteracoes, useReverterInteracao } from "@/lib/hooks/use-ia";

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const TODOS = "__todos__";

function fmtDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STATUS_META: Record<AgentInteractionStatus, { label: string; variant: "secondary" | "destructive" | "outline" }> = {
  ok: { label: "OK", variant: "secondary" },
  erro: { label: "Erro", variant: "destructive" },
  revertido: { label: "Revertido", variant: "outline" },
};

export function AuditoriaView() {
  const [obraId, setObraId] = React.useState<string | null>(null);
  const [agent, setAgent] = React.useState<string | null>(null);
  const obrasQuery = useObras({});
  const interacoesQuery = useInteracoes(obraId, agent);
  const reverter = useReverterInteracao(obraId, agent);

  const obras = obrasQuery.data?.items ?? [];
  const rows = interacoesQuery.data?.items ?? [];

  return (
    <div className="space-y-5">
      <header className="flex items-start gap-3">
        <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
          <ShieldCheck className="size-5" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Auditoria IA</h1>
          <p className="text-sm text-muted-foreground">
            Toda ação dos agentes é registrada (US-22). Reverta ações indevidas com um clique.
          </p>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        <Select
          value={obraId ?? TODOS}
          onValueChange={(v) => setObraId(v === TODOS ? null : v)}
        >
          <SelectTrigger size="sm" className="w-56">
            <SelectValue placeholder="Todas as obras" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todas as obras</SelectItem>
            {obras.map((o) => (
              <SelectItem key={o.id} value={o.id}>
                {o.codigo} · {o.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={agent ?? TODOS} onValueChange={(v) => setAgent(v === TODOS ? null : v)}>
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="Todos os agentes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos os agentes</SelectItem>
            <SelectItem value="orcamento">Orçamento</SelectItem>
            <SelectItem value="compras">Compras</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        {interacoesQuery.isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted-foreground">
            Nenhuma interação registrada para este filtro.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quando</TableHead>
                  <TableHead>Número</TableHead>
                  <TableHead>Comando</TableHead>
                  <TableHead>Agente</TableHead>
                  <TableHead>Resultado</TableHead>
                  <TableHead>Custo</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((it) => (
                  <Row
                    key={it.id}
                    interacao={it}
                    revertendo={reverter.isPending && reverter.variables === it.id}
                    onReverter={() => reverter.mutate(it.id)}
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({
  interacao,
  revertendo,
  onReverter,
}: {
  interacao: AgentInteraction;
  revertendo: boolean;
  onReverter: () => void;
}) {
  const meta = STATUS_META[interacao.status];
  const podeReverter = interacao.action !== null && interacao.reverted_at === null;
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-muted-foreground">
        {fmtDataHora(interacao.created_at)}
      </TableCell>
      <TableCell className="whitespace-nowrap tabular-nums">{interacao.whatsapp_number}</TableCell>
      <TableCell className="max-w-40 truncate" title={interacao.command}>
        {interacao.command}
      </TableCell>
      <TableCell>
        <span className="inline-flex items-center gap-1.5 text-sm">
          <Bot className="size-3.5 text-muted-foreground" />
          {interacao.agent ?? "—"}
        </span>
        {interacao.obra_codigo ? (
          <span className="ml-1 text-xs text-muted-foreground">· {interacao.obra_codigo}</span>
        ) : null}
      </TableCell>
      <TableCell className="max-w-44 truncate text-muted-foreground" title={interacao.result ?? ""}>
        {interacao.result ?? "—"}
      </TableCell>
      <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
        {BRL.format(interacao.cost_cents / 100)}
      </TableCell>
      <TableCell>
        <Badge variant={meta.variant}>{meta.label}</Badge>
      </TableCell>
      <TableCell className="text-right">
        {podeReverter ? (
          <Button variant="outline" size="sm" onClick={onReverter} disabled={revertendo}>
            {revertendo ? <Loader2 className="animate-spin" /> : <RotateCcw />}
            Reverter
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
    </TableRow>
  );
}
