"use client";

import * as React from "react";
import { Check, FileText, Loader2, X } from "lucide-react";

import { PortalNav } from "@/components/portal/PortalNav";
import { PortalObraHeader } from "@/components/portal/PortalObraHeader";
import { SignaturePad } from "@/components/portal/SignaturePad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { AprovacaoDecisao, PortalAprovacaoInput, PortalOrcamento } from "@/lib/api/types";
import { useDecidirOrcamento, usePortalObra, usePortalOrcamento } from "@/lib/hooks/use-portal";

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function fmtDataHora(s: string | null): string {
  if (!s) return "";
  return new Date(s).toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
}

export function PortalOrcamentoView({ token }: { token: string }) {
  const obraQuery = usePortalObra(token);
  const orcQuery = usePortalOrcamento(token);
  const decidir = useDecidirOrcamento(token);
  const [modal, setModal] = React.useState<AprovacaoDecisao | null>(null);

  const obra = obraQuery.data;

  return (
    <div>
      <PortalNav token={token} />
      {obra ? (
        <PortalObraHeader
          construtora={obra.construtora}
          nome={obra.nome}
          codigo={obra.codigo}
          status={obra.status}
        />
      ) : null}

      {orcQuery.isLoading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : orcQuery.isError || !orcQuery.data ? (
        <div className="rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          Nenhum orçamento disponível para aprovação no momento.
        </div>
      ) : (
        <OrcamentoCard
          orcamento={orcQuery.data}
          onDecidir={(d) => setModal(d)}
          decidindo={decidir.isPending}
        />
      )}

      {modal ? (
        <DecisaoModal
          decisao={modal}
          pending={decidir.isPending}
          onClose={() => setModal(null)}
          onConfirm={(body) =>
            decidir.mutate(
              { decisao: modal, body },
              { onSuccess: () => setModal(null) },
            )
          }
        />
      ) : null}
    </div>
  );
}

function OrcamentoCard({
  orcamento,
  onDecidir,
  decidindo,
}: {
  orcamento: PortalOrcamento;
  onDecidir: (d: AprovacaoDecisao) => void;
  decidindo: boolean;
}) {
  const aguardando = orcamento.status === "aguardando_aprovacao";
  const decidido = orcamento.decisao !== null;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="border-b border-border p-4">
        <p className="text-xs font-medium text-muted-foreground">Orçamento</p>
        <h2 className="mt-0.5 text-lg font-bold">{orcamento.titulo}</h2>
        <p className="mt-3 text-3xl font-extrabold tracking-tight tabular-nums">
          {BRL.format(Number(orcamento.preco_venda))}
        </p>
      </div>

      {decidido ? (
        <div
          className={
            orcamento.decisao === "aprovado"
              ? "flex items-center gap-2 bg-success/10 px-4 py-3 text-sm font-medium text-success"
              : "flex items-center gap-2 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive"
          }
        >
          {orcamento.decisao === "aprovado" ? <Check className="size-4" /> : <X className="size-4" />}
          {orcamento.decisao === "aprovado" ? "Aprovado" : "Rejeitado"} em{" "}
          {fmtDataHora(orcamento.decidido_em)}
        </div>
      ) : null}

      {/* Visualizador do PDF timbrado. */}
      {orcamento.pdf_url ? (
        <iframe
          title="PDF do orçamento"
          src={orcamento.pdf_url}
          className="h-[420px] w-full border-b border-border bg-white"
        />
      ) : (
        <div className="flex items-center gap-2 border-b border-border px-4 py-8 text-sm text-muted-foreground">
          <FileText className="size-4" /> PDF ainda não disponível.
        </div>
      )}

      {aguardando ? (
        <div className="flex gap-2 p-4">
          <Button
            variant="destructive"
            size="lg"
            className="flex-1"
            onClick={() => onDecidir("rejeitado")}
            disabled={decidindo}
          >
            <X /> Rejeitar
          </Button>
          <Button
            size="lg"
            className="flex-1"
            onClick={() => onDecidir("aprovado")}
            disabled={decidindo}
          >
            <Check /> Aprovar
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function DecisaoModal({
  decisao,
  pending,
  onClose,
  onConfirm,
}: {
  decisao: AprovacaoDecisao;
  pending: boolean;
  onClose: () => void;
  onConfirm: (body: PortalAprovacaoInput) => void;
}) {
  const aprovar = decisao === "aprovado";
  const [comentario, setComentario] = React.useState("");
  const [assinadoPor, setAssinadoPor] = React.useState("");
  const [assinatura, setAssinatura] = React.useState<string | null>(null);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-border bg-card p-5 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold">
          {aprovar ? "Aprovar orçamento" : "Rejeitar orçamento"}
        </h3>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {aprovar
            ? "Ao aprovar, a construtora é notificada e a versão é fixada."
            : "Descreva o motivo para a construtora revisar o orçamento."}
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Comentário (opcional)</label>
            <Textarea
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              placeholder={aprovar ? "Alguma observação?" : "Motivo da rejeição"}
              rows={3}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Seu nome</label>
            <Input
              value={assinadoPor}
              onChange={(e) => setAssinadoPor(e.target.value)}
              placeholder="Nome de quem aprova"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Assinatura (opcional)</label>
            <SignaturePad onChange={setAssinatura} />
          </div>
        </div>

        <div className="mt-5 flex gap-2">
          <Button variant="outline" size="lg" className="flex-1" onClick={onClose} disabled={pending}>
            Cancelar
          </Button>
          <Button
            variant={aprovar ? "default" : "destructive"}
            size="lg"
            className="flex-1"
            disabled={pending}
            onClick={() =>
              onConfirm({
                comentario: comentario.trim() || null,
                assinado_por: assinadoPor.trim() || null,
                assinatura,
              })
            }
          >
            {pending ? <Loader2 className="animate-spin" /> : null}
            {aprovar ? "Confirmar aprovação" : "Confirmar rejeição"}
          </Button>
        </div>
      </div>
    </div>
  );
}
