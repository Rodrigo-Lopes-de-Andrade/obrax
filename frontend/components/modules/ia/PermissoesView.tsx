"use client";

import * as React from "react";
import { KeyRound, Loader2, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { AiRole } from "@/lib/api/types";
import { useCriarPermissao, usePermissoes, useRemoverPermissao } from "@/lib/hooks/use-ia";

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

const ROLE_META: Record<AiRole, { label: string; desc: string }> = {
  consultor: { label: "Consultor", desc: "Só consulta (status, orçamento)" },
  solicitador: { label: "Solicitador", desc: "Consulta + cria solicitações de compra" },
  aprovador: { label: "Aprovador", desc: "Consulta, solicita e aprova" },
};

/** Reais (string do input) → centavos inteiros. Vazio = 0 (sem limite). */
function reaisToCents(v: string): number {
  const n = Number(v.replace(",", "."));
  return Number.isFinite(n) && n > 0 ? Math.round(n * 100) : 0;
}

export function PermissoesView() {
  const { data, isLoading } = usePermissoes();
  const criar = useCriarPermissao();
  const remover = useRemoverPermissao();

  const [numero, setNumero] = React.useState("");
  const [role, setRole] = React.useState<AiRole>("consultor");
  const [diario, setDiario] = React.useState("");
  const [mensal, setMensal] = React.useState("");

  const permissoes = data?.items ?? [];

  function adicionar() {
    const n = numero.trim();
    if (!n || criar.isPending) return;
    criar.mutate(
      {
        whatsapp_number: n,
        role,
        daily_limit_cents: reaisToCents(diario),
        monthly_limit_cents: reaisToCents(mensal),
      },
      {
        onSuccess: () => {
          setNumero("");
          setDiario("");
          setMensal("");
          setRole("consultor");
        },
      },
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="flex items-start gap-3">
        <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
          <KeyRound className="size-5" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Permissões IA</h1>
          <p className="text-sm text-muted-foreground">
            Autorize números de WhatsApp a usar os agentes e defina limites de gasto (US-23).
          </p>
        </div>
      </header>

      {/* Formulário de nova permissão. */}
      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-bold">Autorizar número</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">WhatsApp</label>
            <Input
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
              placeholder="+55 11 90000-0000"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Papel</label>
            <Select value={role} onValueChange={(v) => setRole(v as AiRole)}>
              <SelectTrigger className="w-full" aria-label="Papel">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(ROLE_META) as AiRole[]).map((r) => (
                  <SelectItem key={r} value={r}>
                    {ROLE_META[r].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Limite diário (R$, 0 = sem limite)
            </label>
            <Input
              value={diario}
              onChange={(e) => setDiario(e.target.value)}
              inputMode="decimal"
              placeholder="0,00"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Limite mensal (R$, 0 = sem limite)
            </label>
            <Input
              value={mensal}
              onChange={(e) => setMensal(e.target.value)}
              inputMode="decimal"
              placeholder="0,00"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{ROLE_META[role].desc}.</p>
        <Button className="mt-3" onClick={adicionar} disabled={!numero.trim() || criar.isPending}>
          {criar.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
          Autorizar
        </Button>
      </section>

      {/* Lista de permissões. */}
      <section>
        <h2 className="mb-2 text-sm font-bold">Números autorizados</h2>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        ) : permissoes.length === 0 ? (
          <p className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
            Nenhum número autorizado ainda.
          </p>
        ) : (
          <ul className="space-y-2">
            {permissoes.map((p) => (
              <li
                key={p.id}
                className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium tabular-nums">{p.whatsapp_number}</span>
                    <Badge variant="secondary">{ROLE_META[p.role].label}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Limite: {p.daily_limit_cents ? BRL.format(p.daily_limit_cents / 100) : "sem"}/dia
                    {" · "}
                    {p.monthly_limit_cents ? BRL.format(p.monthly_limit_cents / 100) : "sem"}/mês
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Remover ${p.whatsapp_number}`}
                  onClick={() => remover.mutate(p.id)}
                  disabled={remover.isPending}
                >
                  <Trash2 className="text-muted-foreground" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
