/**
 * Mock dos relatórios gerenciais (B6.5, US-10). Espelha
 * gestao/relatorios/service.py: agrega obras/orçamentos por status (breakdown
 * zero-preenchido na ordem do enum) em Decimal.js. O filtro de período incide
 * sobre `created_at` (o backend real só passa a filtrar quando os endpoints
 * aceitarem `from`/`to`; params desconhecidos são ignorados pelo FastAPI).
 */
import Decimal from "decimal.js";

import type {
  ObraStatus,
  OrcamentoStatus,
  RelatorioObrasAtivas,
  RelatorioOrcamentos,
} from "@/lib/api/types";
import { obras } from "./db";
import { orcamentos, versoes } from "./orcamento-mock";

const OBRA_STATUS: ObraStatus[] = [
  "planejamento",
  "execucao",
  "pausada",
  "concluida",
  "cancelada",
];
const OBRA_INATIVAS = new Set<ObraStatus>(["concluida", "cancelada"]);
const ORCAMENTO_STATUS: OrcamentoStatus[] = [
  "rascunho",
  "em_revisao",
  "aguardando_aprovacao",
  "aprovado",
  "rejeitado",
];

function inRange(iso: string, from: string | null, to: string | null): boolean {
  const d = iso.slice(0, 10);
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

export function relatorioObrasAtivas(
  from: string | null,
  to: string | null,
): RelatorioObrasAtivas {
  const rows = obras.filter((o) => inRange(o.created_at, from, to));
  const por_status = OBRA_STATUS.map((status) => {
    const grupo = rows.filter((o) => o.status === status);
    const valor = grupo.reduce((a, o) => a.plus(o.valor_contrato ?? 0), new Decimal(0));
    return { status, count: grupo.length, valor: valor.toFixed(2) };
  });
  const ativas = por_status.filter((l) => !OBRA_INATIVAS.has(l.status));
  const valorAtivas = ativas.reduce((a, l) => a.plus(l.valor), new Decimal(0));
  return {
    ativas: ativas.reduce((a, l) => a + l.count, 0),
    valor_ativas: valorAtivas.toFixed(2),
    total: por_status.reduce((a, l) => a + l.count, 0),
    por_status,
  };
}

export function relatorioOrcamentos(
  from: string | null,
  to: string | null,
): RelatorioOrcamentos {
  const rows = orcamentos.filter((o) => !o.deleted && inRange(o.created_at, from, to));
  const precoDe = (orcamentoId: string, versaoAtual: number): Decimal => {
    const v = versoes.find((x) => x.orcamento_id === orcamentoId && x.numero === versaoAtual);
    return new Decimal(v?.preco_venda ?? 0);
  };
  const por_status = ORCAMENTO_STATUS.map((status) => {
    const grupo = rows.filter((o) => o.status === status);
    const preco = grupo.reduce((a, o) => a.plus(precoDe(o.id, o.versao_atual)), new Decimal(0));
    return { status, count: grupo.length, preco_venda: preco.toFixed(2) };
  });
  const pendentes =
    por_status.find((l) => l.status === "aguardando_aprovacao")?.count ?? 0;
  return {
    total: por_status.reduce((a, l) => a + l.count, 0),
    preco_venda_total: por_status
      .reduce((a, l) => a.plus(l.preco_venda), new Decimal(0))
      .toFixed(2),
    pendentes,
    por_status,
  };
}
