"use client";

import * as React from "react";
import { ChevronDown, Loader2, MessagesSquare, Send } from "lucide-react";

import { PortalNav } from "@/components/portal/PortalNav";
import { PortalObraHeader } from "@/components/portal/PortalObraHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TicketStatusBadge } from "@/components/modules/ticket/status";
import { Textarea } from "@/components/ui/textarea";
import type { PortalTicket, TicketMensagem } from "@/lib/api/types";
import { useAddPortalMensagem, usePortalObra, usePortalTickets } from "@/lib/hooks/use-portal";
import { cn } from "@/lib/utils";

function fmtDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PortalTicketsView({ token }: { token: string }) {
  const obraQuery = usePortalObra(token);
  const ticketsQuery = usePortalTickets(token);
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

      <h2 className="mb-2 text-sm font-bold">Chamados</h2>
      {ticketsQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      ) : ticketsQuery.isError ? (
        <p className="rounded-xl border border-border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
          Não foi possível carregar os chamados.
        </p>
      ) : !ticketsQuery.data || ticketsQuery.data.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          <MessagesSquare className="size-6" />
          Nenhum chamado aberto para esta obra.
        </div>
      ) : (
        <ul className="space-y-2">
          {ticketsQuery.data.map((t) => (
            <TicketItem key={t.id} token={token} ticket={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TicketItem({ token, ticket }: { token: string; ticket: PortalTicket }) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const addMensagem = useAddPortalMensagem(token);
  const fechado = ticket.status === "fechado";

  function send() {
    const content = text.trim();
    if (!content || addMensagem.isPending) return;
    addMensagem.mutate(
      { ticketId: ticket.id, body: { content } },
      { onSuccess: () => setText("") },
    );
  }

  return (
    <li className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{ticket.titulo}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Aberto em {fmtDataHora(ticket.created_at)} · {ticket.mensagens.length}{" "}
            {ticket.mensagens.length === 1 ? "mensagem" : "mensagens"}
          </p>
        </div>
        <TicketStatusBadge status={ticket.status} />
        <ChevronDown
          className={cn(
            "size-4 flex-shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open ? (
        <div className="border-t border-border">
          <div className="space-y-3 px-4 py-3">
            {ticket.mensagens.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Ainda sem mensagens neste chamado.
              </p>
            ) : (
              ticket.mensagens.map((m) => <MensagemBubble key={m.id} mensagem={m} />)
            )}
          </div>

          {fechado ? (
            <p className="border-t border-border px-4 py-3 text-center text-xs text-muted-foreground">
              Este chamado está fechado.
            </p>
          ) : (
            <div className="flex items-end gap-2 border-t border-border p-3">
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={1}
                placeholder="Escreva uma mensagem…"
                className="max-h-32 min-h-9 resize-none"
              />
              <Button
                onClick={send}
                disabled={!text.trim() || addMensagem.isPending}
                aria-label="Enviar mensagem"
              >
                {addMensagem.isPending ? <Loader2 className="animate-spin" /> : <Send />}
              </Button>
            </div>
          )}
        </div>
      ) : null}
    </li>
  );
}

/** No portal, mensagens do cliente têm `author_id: null` → alinhadas à direita. */
function MensagemBubble({ mensagem }: { mensagem: TicketMensagem }) {
  const mine = mensagem.author_id === null;
  return (
    <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[80%] space-y-1", mine ? "items-end" : "items-start")}>
        <p
          className={cn(
            "text-xs text-muted-foreground",
            mine ? "text-right" : "text-left",
          )}
        >
          {mine ? "Você" : "Construtora"} · {fmtDataHora(mensagem.created_at)}
        </p>
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
            mine
              ? "rounded-tr-sm bg-primary/90 text-primary-foreground"
              : "rounded-tl-sm bg-muted text-foreground",
          )}
        >
          {mensagem.content}
        </div>
      </div>
    </div>
  );
}
