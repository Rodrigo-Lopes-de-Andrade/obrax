"use client";

import * as React from "react";
import { Bot, Loader2, Send, Sparkles } from "lucide-react";

import { Avatar } from "@/components/shared/Avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { AgentChatMessage } from "@/lib/api/types";
import { useAssistenteThread, useEnviarAssistenteMensagem } from "@/lib/hooks/use-ia";
import { capture } from "@/lib/observability/analytics";
import { cn } from "@/lib/utils";

const SUGESTOES = [
  "Qual o status da obra Vila Aurora?",
  "Quanto custou o orçamento aprovado?",
  "Solicitar 20 sacos de cimento para o galpão",
];

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function AssistenteView() {
  const threadQuery = useAssistenteThread();
  const enviar = useEnviarAssistenteMensagem();
  const [text, setText] = React.useState("");
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const mensagens = threadQuery.data ?? [];

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens.length, enviar.isPending]);

  function send(content: string) {
    const c = content.trim();
    if (!c || enviar.isPending) return;
    enviar.mutate(c);
    capture("assistente_mensagem_enviada", { chars: c.length });
    setText("");
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <header className="mb-4 flex items-start gap-3">
        <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
          <Bot className="size-5" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Assistente IA</h1>
          <p className="text-sm text-muted-foreground">
            Consulte status de obras, resumos de orçamento e registre solicitações de compra.
          </p>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-card">
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
          {threadQuery.isLoading ? (
            <ChatSkeleton />
          ) : mensagens.length === 0 ? (
            <EmptyState onPick={(s) => send(s)} />
          ) : (
            mensagens.map((m) => <Bubble key={m.id} mensagem={m} />)
          )}
          {enviar.isPending ? <TypingBubble /> : null}
          <div ref={bottomRef} />
        </div>

        <div className="flex items-end gap-2 border-t border-border p-3">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(text);
              }
            }}
            rows={1}
            placeholder="Pergunte ao assistente…  (Enter envia)"
            className="max-h-32 min-h-9 resize-none"
          />
          <Button
            onClick={() => send(text)}
            disabled={!text.trim() || enviar.isPending}
            aria-label="Enviar"
          >
            {enviar.isPending ? <Loader2 className="animate-spin" /> : <Send />}
          </Button>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
        <Sparkles className="size-6" />
      </div>
      <p className="max-w-sm text-sm text-muted-foreground">
        Comece com uma pergunta ou escolha uma sugestão abaixo.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {SUGESTOES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function Bubble({ mensagem }: { mensagem: AgentChatMessage }) {
  const mine = mensagem.role === "user";
  return (
    <div className={cn("flex gap-2.5", mine ? "flex-row-reverse" : "flex-row")}>
      {mine ? (
        <Avatar name="Você" variant="gradient" className="size-8" />
      ) : (
        <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
          <Bot className="size-4" />
        </div>
      )}
      <div className={cn("max-w-[78%] space-y-1", mine ? "items-end" : "items-start")}>
        <div
          className={cn(
            "flex items-baseline gap-2 text-xs",
            mine ? "flex-row-reverse" : "flex-row",
          )}
        >
          <span className="font-medium text-foreground">{mine ? "Você" : "Assistente"}</span>
          <span className="text-muted-foreground">{formatTime(mensagem.created_at)}</span>
        </div>
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

function TypingBubble() {
  return (
    <div className="flex gap-2.5">
      <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
        <Bot className="size-4" />
      </div>
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-muted px-4 py-3">
        {[0, 150, 300].map((d) => (
          <span
            key={d}
            className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60"
            style={{ animationDelay: `${d}ms` }}
          />
        ))}
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
          <Skeleton className="h-14 w-56 rounded-2xl" />
        </div>
      ))}
    </div>
  );
}
