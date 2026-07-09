"use client";

import { Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { OrcamentoItem, OrcamentoStatus, VersaoResumo } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/format";
import { useUpdateOrcamentoStatus } from "@/lib/hooks/use-orcamentos";
import { OrcamentoStatusBadge } from "../status";

interface Props {
  orcamentoId: string;
  status: OrcamentoStatus;
  versao: VersaoResumo;
  itens: OrcamentoItem[];
}

export function ResumoTab({ orcamentoId, status, versao, itens }: Props) {
  const updateStatus = useUpdateOrcamentoStatus();
  const fases = itens.filter((i) => i.tipo === "F");
  const totalFases = fases.reduce((sum, f) => sum + Number(f.subtotal), 0);
  const podeEnviar = status === "rascunho" || status === "em_revisao";

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-6 overflow-y-auto lg:grid-cols-[1fr_20rem]">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Resumo por fase</h2>
          <OrcamentoStatusBadge status={status} />
        </div>
        <div className="overflow-hidden rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Fase</TableHead>
                <TableHead className="text-right">Subtotal</TableHead>
                <TableHead className="text-right">% do total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fases.length === 0 ? (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={3} className="h-20 text-center text-sm text-muted-foreground">
                    Sem fases para resumir.
                  </TableCell>
                </TableRow>
              ) : (
                fases.map((f) => {
                  const pct = totalFases > 0 ? Number(f.subtotal) / totalFases : 0;
                  return (
                    <TableRow key={f.id}>
                      <TableCell className="font-medium">{f.descricao}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(f.subtotal)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {formatPercent(pct, 1)}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <aside className="h-fit space-y-4 rounded-xl border border-border bg-card p-5">
        <div className="text-sm font-semibold">Resumo financeiro</div>
        <dl className="space-y-2 text-sm">
          <Row label="Custo direto" value={formatMoney(versao.custo_direto)} />
          <Row label="Markup global" value={formatPercent(versao.markup_global)} muted />
          <Row label="Taxa administrativa" value={formatPercent(versao.taxa_adm)} muted />
          <div className="border-t border-border pt-2">
            <Row label="Preço de venda" value={formatMoney(versao.preco_venda)} emphasis />
          </div>
          <Row label="Margem" value={formatPercent(versao.margem)} />
        </dl>

        <Button
          className="w-full"
          disabled={!podeEnviar || updateStatus.isPending}
          onClick={() =>
            updateStatus.mutate({ id: orcamentoId, status: "aguardando_aprovacao" })
          }
        >
          {updateStatus.isPending ? <Loader2 className="animate-spin" /> : <Send />}
          Enviar para aprovação
        </Button>
        {!podeEnviar ? (
          <p className="text-center text-xs text-muted-foreground">
            {status === "aguardando_aprovacao"
              ? "Aguardando decisão do cliente."
              : status === "aprovado"
                ? "Orçamento aprovado e travado."
                : "Reabra em revisão para reenviar."}
          </p>
        ) : null}
      </aside>
    </div>
  );
}

function Row({
  label,
  value,
  muted,
  emphasis,
}: {
  label: string;
  value: string;
  muted?: boolean;
  emphasis?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className={muted ? "text-muted-foreground" : ""}>{label}</dt>
      <dd
        className={
          emphasis
            ? "text-lg font-semibold text-primary tabular-nums"
            : "font-medium tabular-nums"
        }
      >
        {value}
      </dd>
    </div>
  );
}
