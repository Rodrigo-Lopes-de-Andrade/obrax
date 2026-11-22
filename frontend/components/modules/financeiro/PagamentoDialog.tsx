"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DespesaOut } from "@/lib/api/types";
import { formatMoney } from "@/lib/decimal";
import { usePagarDespesa } from "@/lib/hooks/use-despesas";

function hojeIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

interface PagamentoDialogProps {
  despesa: DespesaOut | null;
  obraId: string;
  onClose: () => void;
}

/** CA-F09.1: pede a data; o valor pago é o do título. */
export function PagamentoDialog({ despesa, obraId, onClose }: PagamentoDialogProps) {
  const pagar = usePagarDespesa(obraId);
  const [data, setData] = React.useState(hojeIso());
  const [erro, setErro] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (despesa) {
      setData(hojeIso());
      setErro(null);
    }
  }, [despesa]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!despesa) return;
    if (!data) return setErro("Informe a data do pagamento");
    pagar.mutate({ id: despesa.id, data: { data_pagamento: data } }, { onSuccess: onClose });
  }

  return (
    <AlertDialog open={despesa !== null} onOpenChange={(o) => (!o && !pagar.isPending ? onClose() : undefined)}>
      <AlertDialogContent>
        <form onSubmit={submit} className="space-y-4" noValidate>
          <AlertDialogHeader>
            <AlertDialogTitle>Registrar pagamento</AlertDialogTitle>
            <AlertDialogDescription>
              {despesa
                ? `${despesa.descricao} — ${formatMoney(despesa.valor)} (valor do título).`
                : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="data-pagamento">Data do pagamento</Label>
            <Input
              id="data-pagamento"
              type="date"
              value={data}
              aria-invalid={erro ? true : undefined}
              onChange={(e) => {
                setData(e.target.value);
                setErro(null);
              }}
            />
            {erro ? (
              <p role="alert" className="text-sm text-destructive">
                {erro}
              </p>
            ) : null}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel type="button" disabled={pagar.isPending}>
              Cancelar
            </AlertDialogCancel>
            <Button type="submit" disabled={pagar.isPending}>
              {pagar.isPending ? <Loader2 className="animate-spin" /> : null}
              Confirmar pagamento
            </Button>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  );
}
