"use client";

import * as React from "react";
import { Banknote, Pencil, Undo2, XCircle } from "lucide-react";

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
import type { DespesaOut, DespesaStatus } from "@/lib/api/types";
import { formatMoney } from "@/lib/decimal";
import { formatDate } from "@/lib/format";

const STATUS: Record<DespesaStatus, { label: string; variant: "outline" | "secondary" | "destructive" }> = {
  prevista: { label: "Prevista", variant: "outline" },
  paga: { label: "Paga", variant: "secondary" },
  cancelada: { label: "Cancelada", variant: "destructive" },
};

export function DespesaStatusBadge({ status }: { status: DespesaStatus }) {
  const s = STATUS[status];
  return <Badge variant={s.variant}>{s.label}</Badge>;
}

/** Parcelas repetem a descrição: "(n/N)" distingue o nome acessível dos botões. */
function nomeAcessivel(d: DespesaOut): string {
  return d.parcela_num != null && d.parcela_total != null
    ? `${d.descricao} (${d.parcela_num}/${d.parcela_total})`
    : d.descricao;
}

interface ConfirmActionProps {
  label: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
}

function ConfirmAction({ label, icon, title, description, confirmLabel, onConfirm }: ConfirmActionProps) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={label} title={label} className="text-muted-foreground">
          {icon}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Voltar</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface DespesasTableProps {
  items: DespesaOut[];
  loading: boolean;
  /** Só FIN (owner/admin/financeiro) paga, cancela e estorna (E-10). */
  canFin: boolean;
  /** `gestor` e FIN lançam e editam. */
  canEdit: boolean;
  onEdit: (d: DespesaOut) => void;
  onPagar: (d: DespesaOut) => void;
  onCancelar: (d: DespesaOut) => void;
  onEstornar: (d: DespesaOut) => void;
}

export function DespesasTable({
  items,
  loading,
  canFin,
  canEdit,
  onEdit,
  onPagar,
  onCancelar,
  onEstornar,
}: DespesasTableProps) {
  return (
    <div className="rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Vencimento</TableHead>
            <TableHead>Descrição</TableHead>
            <TableHead>Fase</TableHead>
            <TableHead>Categoria</TableHead>
            <TableHead>Fornecedor</TableHead>
            <TableHead className="text-right">Valor</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Ações</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({ length: 5 }, (_, i) => (
                <TableRow key={i} aria-hidden>
                  {Array.from({ length: 8 }, (_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : items.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="whitespace-nowrap">{formatDate(d.vencimento)}</TableCell>
                  <TableCell>
                    {d.descricao}
                    {d.parcela_num != null && d.parcela_total != null ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {d.parcela_num}/{d.parcela_total}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>{d.fase_descricao}</TableCell>
                  <TableCell>{d.categoria_nome}</TableCell>
                  <TableCell>{d.fornecedor_nome}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatMoney(d.valor)}</TableCell>
                  <TableCell>
                    <DespesaStatusBadge status={d.status} />
                    {d.status === "paga" && d.data_pagamento ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        em {formatDate(d.data_pagamento)}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-0.5">
                      {d.status === "prevista" && canEdit ? (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Editar ${nomeAcessivel(d)}`}
                          title="Editar"
                          className="text-muted-foreground"
                          onClick={() => onEdit(d)}
                        >
                          <Pencil />
                        </Button>
                      ) : null}
                      {d.status === "prevista" && canFin ? (
                        <>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Pagar ${nomeAcessivel(d)}`}
                            title="Registrar pagamento"
                            className="text-muted-foreground"
                            onClick={() => onPagar(d)}
                          >
                            <Banknote />
                          </Button>
                          <ConfirmAction
                            label={`Cancelar ${nomeAcessivel(d)}`}
                            icon={<XCircle />}
                            title="Cancelar despesa?"
                            description="A despesa fica cancelada e sai do comprometido. Essa ação não pode ser desfeita."
                            confirmLabel="Cancelar despesa"
                            onConfirm={() => onCancelar(d)}
                          />
                        </>
                      ) : null}
                      {d.status === "paga" && canFin ? (
                        <ConfirmAction
                          label={`Estornar ${nomeAcessivel(d)}`}
                          icon={<Undo2 />}
                          title="Estornar pagamento?"
                          description="A despesa volta a prevista e deixa de contar no realizado."
                          confirmLabel="Estornar"
                          onConfirm={() => onEstornar(d)}
                        />
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>
    </div>
  );
}
