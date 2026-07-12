"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Paperclip, Send } from "lucide-react";

import { Avatar } from "@/components/shared/Avatar";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { TicketMensagem, TicketStatus } from "@/lib/api/types";
import { useSearchUsuarios } from "@/lib/hooks/use-membros";
import { useObra } from "@/lib/hooks/use-obras";
import { useMe } from "@/lib/hooks/use-session";
import {
  useCreateMensagem,
  useMensagens,
  useTicket,
  useUpdateTicketStatus,
} from "@/lib/hooks/use-tickets";
import { cn } from "@/lib/utils";
import { TICKET_STATUS_OPTIONS } from "./status";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function TicketChat({ ticketId }: { ticketId: string }) {
  const ticketQuery = useTicket(ticketId);
  const ticket = ticketQuery.data;
  const obraQuery = useObra(ticket?.obra_id ?? "");
  const updateStatus = useUpdateTicketStatus();

  if (ticketQuery.isError) {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        Chamado não encontrado.{" "}
        <Link href="/tickets" className="underline">
          Voltar
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <Button variant="outline" size="icon-sm" asChild aria-label="Voltar">
            <Link href="/tickets">
              <ArrowLeft />
            </Link>
          </Button>
          <div className="min-w-0">
            {ticket ? (
              <>
                <h1 className="truncate text-xl font-semibold tracking-tight">
                  {ticket.titulo}
                </h1>
                <p className="truncate text-sm text-muted-foreground">
                  {obraQuery.data
                    ? `${obraQuery.data.codigo} · ${obraQuery.data.nome}`
                    : "—"}
                </p>
              </>
            ) : (
              <div className="space-y-2">
                <Skeleton className="h-6 w-64" />
                <Skeleton className="h-4 w-40" />
              </div>
            )}
          </div>
        </div>

        {ticket ? (
          <Select
            value={ticket.status}
            onValueChange={(v) =>
              updateStatus.mutate({ id: ticket.id, status: v as TicketStatus })
            }
            disabled={updateStatus.isPending}
          >
            <SelectTrigger size="sm" className="w-40" aria-label="Status do chamado">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TICKET_STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null}
      </div>

      {ticket?.descricao ? (
        <p className="rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          {ticket.descricao}
        </p>
      ) : null}

      <ChatPanel ticketId={ticketId} />
    </div>
  );
}

function ChatPanel({ ticketId }: { ticketId: string }) {
  const { data: me } = useMe();
  const { data: usuariosPage } = useSearchUsuarios("");
  const mensagensQuery = useMensagens(ticketId);
  const createMensagem = useCreateMensagem(ticketId, me);
  const [text, setText] = React.useState("");
  const bottomRef = React.useRef<HTMLDivElement>(null);

  const nameById = React.useMemo(
    () => new Map((usuariosPage?.items ?? []).map((u) => [u.id, u.nome])),
    [usuariosPage],
  );

  // DESC (mais nova primeiro) → exibe cronológico (mais antiga no topo).
  const mensagens = React.useMemo(
    () => [...(mensagensQuery.data?.items ?? [])].reverse(),
    [mensagensQuery.data],
  );

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens.length]);

  function send() {
    const content = text.trim();
    if (!content || createMensagem.isPending) return;
    createMensagem.mutate({ content });
    setText("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
        {mensagensQuery.isLoading ? (
          <ChatSkeleton />
        ) : mensagens.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            Nenhuma mensagem ainda. Comece a conversa.
          </p>
        ) : (
          mensagens.map((m) => (
            <MessageBubble
              key={m.id}
              mensagem={m}
              mine={m.author_id === me?.id}
              authorName={
                m.author_id ? (nameById.get(m.author_id) ?? "Usuário") : "Sistema"
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex items-end gap-2 border-t border-border p-3">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Escreva uma mensagem…  (Enter envia, Shift+Enter quebra linha)"
          className="max-h-32 min-h-9 resize-none"
        />
        <Button
          onClick={send}
          disabled={!text.trim() || createMensagem.isPending}
          aria-label="Enviar"
        >
          {createMensagem.isPending ? <Loader2 className="animate-spin" /> : <Send />}
        </Button>
      </div>
    </div>
  );
}

function MessageBubble({
  mensagem,
  mine,
  authorName,
}: {
  mensagem: TicketMensagem;
  mine: boolean;
  authorName: string;
}) {
  const optimistic = mensagem.id.startsWith("optimistic-");
  return (
    <div className={cn("flex gap-2.5", mine ? "flex-row-reverse" : "flex-row")}>
      <Avatar
        name={authorName}
        variant={mine ? "gradient" : "muted"}
        className="size-8"
      />
      <div className={cn("max-w-[72%] space-y-1", mine ? "items-end" : "items-start")}>
        <div
          className={cn(
            "flex items-baseline gap-2 text-xs",
            mine ? "flex-row-reverse" : "flex-row",
          )}
        >
          <span className="font-medium text-foreground">{mine ? "Você" : authorName}</span>
          <span className="text-muted-foreground">{formatTime(mensagem.created_at)}</span>
        </div>
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
            mine
              ? "rounded-tr-sm bg-primary/90 text-primary-foreground"
              : "rounded-tl-sm bg-muted text-foreground",
            optimistic && "opacity-60",
          )}
        >
          {mensagem.content}
        </div>
        {mensagem.attachment_paths.length > 0 ? (
          <div className={cn("flex flex-wrap gap-1.5", mine ? "justify-end" : "justify-start")}>
            {mensagem.attachment_paths.map((path) => (
              <span
                key={path}
                className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs text-muted-foreground"
              >
                <Paperclip className="size-3" />
                {path.split("/").pop()}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ChatSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className={cn("flex gap-2.5", i % 2 ? "flex-row-reverse" : "")}>
          <Skeleton className="size-8 rounded-full" />
          <Skeleton className="h-14 w-52 rounded-2xl" />
        </div>
      ))}
    </div>
  );
}
