"use client";

import Decimal from "decimal.js";
import { AlertTriangle } from "lucide-react";
import { useRef } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney, formatPercent, sum } from "@/lib/decimal";
import type { AlocacaoIn, CronogramaGradeOut, FaseGradeOut } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/**
 * Percentuais do contrato são FRAÇÕES ("0.2500" = 25%). A célula edita em
 * percentual (0–100, até 2 casas = 4 casas de fração) e converte na borda.
 * Toda conta é Decimal.js. `formatPercent` de `lib/decimal` não multiplica por
 * 100 (o de `lib/format` multiplica e usa Number — não usar aqui), então o
 * chamador passa a fração já ×100.
 */
const UM = new Decimal(1);
const CEM = new Decimal(100);
const CELULA_RE = /^\d{1,3}(?:[.,]\d{1,2})?$/;

export type Draft = Record<string, string>;

export const chaveCelula = (faseId: string, periodoId: string) => `${faseId}|${periodoId}`;

const pct = (fracao: Decimal) => formatPercent(fracao.mul(CEM), 2);

function textoBase(fracao: string | undefined): string {
  if (fracao === undefined) return "0";
  return new Decimal(fracao).mul(CEM).toDecimalPlaces(2).toString().replace(".", ",");
}

/** Texto da célula → fração; `null` se inválido. Vazio vale 0. */
function paraFracao(texto: string): Decimal | null {
  const t = texto.trim();
  if (t === "") return new Decimal(0);
  if (!CELULA_RE.test(t)) return null;
  const p = new Decimal(t.replace(",", "."));
  return p.gt(CEM) ? null : p.div(CEM);
}

function dataCurta(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

export interface LinhaModelo {
  fase: FaseGradeOut;
  textos: string[];
  invalidas: boolean[];
  valores: Decimal[];
  soma: Decimal;
  somaValor: Decimal;
  ok: boolean;
  mensagem: string | null;
}
export interface Modelo {
  linhas: LinhaModelo[];
  totaisColuna: Decimal[];
  totalGeral: Decimal;
  totalOrcado: Decimal;
  problemas: string[];
}

export function calcularModelo(grade: CronogramaGradeOut, draft: Draft): Modelo {
  const problemas: string[] = [];
  const linhas = grade.fases.map<LinhaModelo>((fase) => {
    const orcado = new Decimal(fase.valor_orcado);
    const base = new Map(fase.alocacoes.map((a) => [a.periodo_id, a]));
    const textos: string[] = [];
    const invalidas: boolean[] = [];
    const fracoes: Decimal[] = [];
    const valores: Decimal[] = [];
    grade.periodos.forEach((per) => {
      const editado = draft[chaveCelula(fase.obra_fase_id, per.id)];
      const salvo = base.get(per.id);
      const texto = editado ?? textoBase(salvo?.percentual_planejado);
      const f = paraFracao(texto);
      textos.push(texto);
      invalidas.push(f === null);
      fracoes.push(f ?? new Decimal(0));
      // Célula não editada: valor do servidor (CA-F02.3). Só a editada mostra a prévia local.
      valores.push(
        editado === undefined
          ? new Decimal(salvo?.valor_planejado ?? 0)
          : orcado.mul(f ?? 0).toDecimalPlaces(2, Decimal.ROUND_HALF_UP),
      );
      if (f === null) {
        problemas.push(
          `Fase ${fase.codigo} ${fase.descricao}, período ${per.numero}: informe um percentual de 0 a 100 com até 2 casas.`,
        );
      }
    });
    const soma = sum(fracoes);
    const ok = soma.eq(UM);
    const dif = UM.minus(soma);
    const mensagem = ok
      ? null
      : `Não soma 100%: ${dif.gt(0) ? "faltam" : "excede em"} ${pct(dif.abs())}`;
    if (mensagem) problemas.push(`Fase ${fase.codigo} ${fase.descricao} soma ${pct(soma)}. ${mensagem}.`);
    return { fase, textos, invalidas, valores, soma, somaValor: sum(valores), ok, mensagem };
  });
  const totaisColuna = grade.periodos.map((_, i) => sum(linhas.map((l) => l.valores[i])));
  return {
    linhas,
    totaisColuna,
    totalGeral: sum(totaisColuna),
    totalOrcado: sum(grade.fases.map((f) => f.valor_orcado)),
    problemas,
  };
}

/** Corpo do PUT: todas as células (o PUT substitui a distribuição). */
export function montarAlocacoes(grade: CronogramaGradeOut, modelo: Modelo): AlocacaoIn[] {
  return modelo.linhas.flatMap((l) =>
    grade.periodos.map((per, i) => ({
      obra_fase_id: l.fase.obra_fase_id,
      periodo_id: per.id,
      percentual_planejado: (paraFracao(l.textos[i]) ?? new Decimal(0)).toFixed(4),
    })),
  );
}

/** O texto digitado difere do salvo? (compara como Decimal, "50" == "50,00") */
export function igualAoBase(grade: CronogramaGradeOut, faseId: string, periodoId: string, texto: string): boolean {
  const fase = grade.fases.find((f) => f.obra_fase_id === faseId);
  const base = fase?.alocacoes.find((a) => a.periodo_id === periodoId)?.percentual_planejado;
  const f = paraFracao(texto);
  return f !== null && f.eq(new Decimal(base ?? 0));
}

interface GridProps {
  grade: CronogramaGradeOut;
  modelo: Modelo;
  somenteLeitura: boolean;
  onChange: (faseId: string, periodoId: string, texto: string) => void;
}

export function CronogramaGrid({ grade, modelo, somenteLeitura, onChange }: GridProps) {
  const tabela = useRef<HTMLDivElement>(null);

  // Tab percorre as células. Setas ↑/↓ andam entre fases e ←/→ entre períodos; ←/→ só
  // saem da célula quando o cursor está na borda do texto (senão movem o cursor).
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>, linha: number, col: number) {
    const el = e.currentTarget;
    let dl = 0;
    let dc = 0;
    if (e.key === "ArrowDown") dl = 1;
    else if (e.key === "ArrowUp") dl = -1;
    else if (e.key === "ArrowRight" && el.selectionEnd === el.value.length) dc = 1;
    else if (e.key === "ArrowLeft" && el.selectionStart === 0) dc = -1;
    else return;
    const alvo = tabela.current?.querySelector<HTMLInputElement>(`[data-cell="${linha + dl}:${col + dc}"]`);
    if (alvo) {
      e.preventDefault();
      alvo.focus();
      alvo.select();
    }
  }

  return (
    <div ref={tabela}>
      <Table>
        <caption className="sr-only">
          Distribuição planejada do orçamento: fases nas linhas, períodos nas colunas, percentuais por célula.
        </caption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Fase</TableHead>
            {grade.periodos.map((p) => (
              <TableHead key={p.id} scope="col" className="min-w-28 text-right">
                Período {p.numero}
                <span className="block text-xs font-normal text-muted-foreground">
                  {dataCurta(p.inicio)} a {dataCurta(p.fim)}
                </span>
              </TableHead>
            ))}
            <TableHead scope="col" className="min-w-40 text-right">
              Total da fase
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {modelo.linhas.map((l, li) => (
            <TableRow key={l.fase.obra_fase_id} className={cn(!l.ok && "bg-destructive/10")}>
              <TableHead scope="row" className="font-normal">
                <span className="font-mono text-xs text-muted-foreground">{l.fase.codigo}</span>{" "}
                <span className="font-medium">{l.fase.descricao}</span>
                <span className="block text-xs text-muted-foreground">
                  Orçado {formatMoney(l.fase.valor_orcado)}
                </span>
              </TableHead>
              {grade.periodos.map((p, ci) => (
                <TableCell key={p.id} className="text-right align-top">
                  <div className="flex items-center justify-end gap-1">
                    <input
                      data-cell={`${li}:${ci}`}
                      type="text"
                      inputMode="decimal"
                      autoComplete="off"
                      readOnly={somenteLeitura}
                      value={l.textos[ci]}
                      aria-label={`Percentual da fase ${l.fase.codigo} ${l.fase.descricao} no período ${p.numero}`}
                      aria-invalid={l.invalidas[ci] || undefined}
                      aria-describedby={l.mensagem ? `cron-msg-${l.fase.obra_fase_id}` : undefined}
                      onChange={(e) => onChange(l.fase.obra_fase_id, p.id, e.target.value)}
                      onFocus={(e) => e.currentTarget.select()}
                      onKeyDown={(e) => onKeyDown(e, li, ci)}
                      className="h-8 w-16 rounded-lg border border-input bg-transparent px-2 text-right text-sm tabular-nums outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 read-only:bg-muted/40 aria-invalid:border-destructive"
                    />
                    <span aria-hidden="true" className="text-xs text-muted-foreground">
                      %
                    </span>
                  </div>
                  <span className="mt-1 block text-xs tabular-nums text-muted-foreground">
                    {formatMoney(l.valores[ci])}
                  </span>
                </TableCell>
              ))}
              <TableCell className="text-right align-top">
                <span className="font-medium tabular-nums">{pct(l.soma)}</span>
                <span className="block text-xs tabular-nums text-muted-foreground">
                  {formatMoney(l.somaValor)}
                </span>
                {l.mensagem ? (
                  <span
                    id={`cron-msg-${l.fase.obra_fase_id}`}
                    className="mt-1 flex items-start justify-end gap-1 text-xs font-medium text-foreground"
                  >
                    <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-destructive" aria-hidden="true" />
                    {l.mensagem}
                  </span>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableHead scope="row">Total do período</TableHead>
            {modelo.totaisColuna.map((t, i) => (
              <TableCell key={grade.periodos[i].id} className="text-right font-medium tabular-nums">
                {formatMoney(t)}
              </TableCell>
            ))}
            <TableCell className="text-right font-medium tabular-nums">
              {formatMoney(modelo.totalGeral)}
              <span className="block text-xs font-normal text-muted-foreground">
                Orçado {formatMoney(modelo.totalOrcado)}
              </span>
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </div>
  );
}
