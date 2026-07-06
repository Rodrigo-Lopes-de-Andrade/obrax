"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import type { Fase } from "@/lib/types/orcamento";
import { formatMoney, multiply, sum } from "@/lib/decimal";

const BDI_MULTIPLIER = 1.245;

interface EapTreeProps {
  fases: Fase[];
  onChange: (fases: Fase[]) => void;
  onOpenImport: () => void;
}

export function EapTree({ fases, onChange, onOpenImport }: EapTreeProps) {
  const [editing, setEditing] = useState<string | null>(null);

  function toggleFase(faseId: string) {
    onChange(fases.map((f) => (f.id === faseId ? { ...f, open: !f.open } : f)));
  }

  function toggleServico(faseId: string, servicoId: string) {
    onChange(
      fases.map((f) =>
        f.id !== faseId
          ? f
          : { ...f, servicos: f.servicos.map((s) => (s.id === servicoId ? { ...s, open: !s.open } : s)) },
      ),
    );
  }

  function editInsumo(faseId: string, servicoId: string, insumoId: string, field: "qtd" | "preco", raw: string) {
    const value = parseFloat(raw.replace(/\./g, "").replace(",", ".")) || 0;
    onChange(
      fases.map((f) =>
        f.id !== faseId
          ? f
          : {
              ...f,
              servicos: f.servicos.map((s) =>
                s.id !== servicoId
                  ? s
                  : {
                      ...s,
                      insumos: s.insumos.map((i) => (i.id === insumoId ? { ...i, [field]: value } : i)),
                    },
              ),
            },
      ),
    );
    const key = `${insumoId}-${field}`;
    setEditing(key);
    window.setTimeout(() => setEditing((current) => (current === key ? null : current)), 700);
  }

  function addInsumo(faseId: string, servicoId: string) {
    const id = `i${Date.now()}`;
    onChange(
      fases.map((f) =>
        f.id !== faseId
          ? f
          : {
              ...f,
              servicos: f.servicos.map((s) =>
                s.id !== servicoId
                  ? s
                  : {
                      ...s,
                      insumos: [...s.insumos, { id, codigo: "—", desc: "Novo insumo", unid: "un", qtd: 0, preco: 0 }],
                    },
              ),
            },
      ),
    );
  }

  function removeInsumo(faseId: string, servicoId: string, insumoId: string) {
    onChange(
      fases.map((f) =>
        f.id !== faseId
          ? f
          : {
              ...f,
              servicos: f.servicos.map((s) =>
                s.id !== servicoId ? s : { ...s, insumos: s.insumos.filter((i) => i.id !== insumoId) },
              ),
            },
      ),
    );
  }

  function addServico(faseId: string) {
    const id = `s${Date.now()}`;
    onChange(
      fases.map((f) =>
        f.id !== faseId ? f : { ...f, servicos: [...f.servicos, { id, nome: "Novo serviço", open: true, insumos: [] }] },
      ),
    );
  }

  function addFase() {
    const id = `f${Date.now()}`;
    onChange([...fases, { id, nome: "NOVA FASE", open: true, servicos: [] }]);
  }

  const faseSubtotals = fases.map((f) => sum(f.servicos.flatMap((s) => s.insumos.map((i) => multiply(i.qtd, i.preco)))));
  const custoDireto = sum(faseSubtotals);
  const comBdi = multiply(custoDireto, BDI_MULTIPLIER);

  return (
    <div>
      <div className="mb-3.5 flex items-center gap-2.25 text-[13px] text-muted-foreground">
        <span className="text-secondary">✎</span>
        Estrutura analítica (EAP): <b className="font-semibold text-secondary">Fase</b> ›{" "}
        <b className="font-semibold text-subtle-foreground">Serviço</b> › Insumo. Edite Qtd. ou Preço — o total
        recalcula na hora.
      </div>

      <div className="overflow-hidden rounded-[10px] border border-white/6">
        <div className="grid grid-cols-[118px_1fr_52px_96px_124px_132px_34px] border-b border-white/6 bg-card text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
          <div className="px-3.5 py-2.75">Código</div>
          <div className="px-3.5 py-2.75">Descrição</div>
          <div className="px-2 py-2.75">Un.</div>
          <div className="px-3.5 py-2.75 text-right">Qtd.</div>
          <div className="px-3.5 py-2.75 text-right">Preço unit.</div>
          <div className="px-3.5 py-2.75 text-right">Total</div>
          <div />
        </div>

        {fases.map((fase, fi) => {
          const faseSubtotal = faseSubtotals[fi];
          return (
            <div key={fase.id}>
              <button
                type="button"
                onClick={() => toggleFase(fase.id)}
                className="flex w-full items-center gap-2.5 border-b border-white/4 border-l-3 border-l-secondary bg-secondary/6 px-3.5 py-2.75 text-left"
              >
                {fase.open ? (
                  <ChevronDown className="h-4 w-4 text-secondary" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-secondary" />
                )}
                <span className="flex-1 text-[13.5px] font-bold">{fase.nome}</span>
                <span className="font-mono text-[13.5px] font-bold text-secondary">{formatMoney(faseSubtotal)}</span>
              </button>

              {fase.open &&
                fase.servicos.map((servico) => {
                  const servicoSubtotal = sum(servico.insumos.map((i) => multiply(i.qtd, i.preco)));
                  return (
                    <div key={servico.id}>
                      <button
                        type="button"
                        onClick={() => toggleServico(fase.id, servico.id)}
                        className="flex w-full items-center gap-2.25 border-b border-white/4 bg-white/2 py-2.25 pr-3.5 pl-7.5 text-left hover:bg-white/4"
                      >
                        {servico.open ? (
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                        <span className="flex-1 text-[13px] font-semibold text-subtle-foreground">{servico.nome}</span>
                        <span className="font-mono text-[13px] font-semibold text-muted-foreground">
                          {formatMoney(servicoSubtotal)}
                        </span>
                      </button>

                      {servico.open && (
                        <>
                          {servico.insumos.map((insumo) => {
                            const qtdEditing = editing === `${insumo.id}-qtd`;
                            const precoEditing = editing === `${insumo.id}-preco`;
                            return (
                              <div
                                key={insumo.id}
                                className="group grid grid-cols-[118px_1fr_52px_96px_124px_132px_34px] items-center border-b border-white/3 hover:bg-white/2"
                              >
                                <div className="py-2 pr-3.5 pl-13.5 font-mono text-xs text-muted-foreground">
                                  {insumo.codigo}
                                </div>
                                <div className="px-3.5 py-2 text-[13px] font-medium">{insumo.desc}</div>
                                <div className="px-2 py-2 text-xs text-muted-foreground">{insumo.unid}</div>
                                <div className="px-2 py-1.25">
                                  <input
                                    type="text"
                                    defaultValue={insumo.qtd}
                                    onInput={(e) => editInsumo(fase.id, servico.id, insumo.id, "qtd", e.currentTarget.value)}
                                    className={`w-full rounded-md border px-2.25 py-1.75 text-right font-mono text-[13px] font-semibold outline-none ${
                                      qtdEditing
                                        ? "border-secondary bg-secondary/18 shadow-[inset_2px_0_0_var(--color-secondary)]"
                                        : "border-white/10 bg-transparent"
                                    }`}
                                  />
                                </div>
                                <div className="px-2 py-1.25">
                                  <input
                                    type="text"
                                    defaultValue={insumo.preco}
                                    onInput={(e) =>
                                      editInsumo(fase.id, servico.id, insumo.id, "preco", e.currentTarget.value)
                                    }
                                    className={`w-full rounded-md border px-2.25 py-1.75 text-right font-mono text-[13px] font-semibold outline-none ${
                                      precoEditing
                                        ? "border-secondary bg-secondary/18 shadow-[inset_2px_0_0_var(--color-secondary)]"
                                        : "border-white/10 bg-transparent"
                                    }`}
                                  />
                                </div>
                                <div className="px-3.5 py-2 text-right font-mono text-[13px] font-bold">
                                  {formatMoney(multiply(insumo.qtd, insumo.preco))}
                                </div>
                                <div className="flex justify-center px-1.5 py-2">
                                  <button
                                    type="button"
                                    onClick={() => removeInsumo(fase.id, servico.id, insumo.id)}
                                    className="text-primary opacity-0 group-hover:opacity-100"
                                  >
                                    <Trash2 className="h-3.75 w-3.75" />
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                          <div className="border-b border-white/3 py-1.75 pr-3.5 pb-2.25 pl-13.5">
                            <AddButton label="Adicionar insumo" onClick={() => addInsumo(fase.id, servico.id)} />
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              {fase.open && (
                <div className="border-b border-white/4 py-2 pr-3.5 pb-2.5 pl-7.5">
                  <AddButton label="Adicionar serviço" onClick={() => addServico(fase.id)} />
                </div>
              )}
            </div>
          );
        })}

        <div className="flex gap-2 border-b border-white/6 bg-[#1b1e27] px-3.5 py-2.5">
          <AddButton label="Adicionar fase" onClick={addFase} />
          <button
            type="button"
            onClick={onOpenImport}
            className="inline-flex items-center gap-1.5 rounded-md border border-white/8 bg-muted px-3.25 py-1.5 text-[12.5px] font-semibold text-subtle-foreground"
          >
            <span className="text-success">⤓</span>
            Importar planilha
          </button>
        </div>

        <div className="flex items-center justify-between bg-card px-4 py-3.5">
          <div className="flex items-baseline gap-3.5">
            <span className="text-[13px] font-bold tracking-wide text-muted-foreground uppercase">
              Custo direto total
            </span>
            <span className="font-mono text-[13px] text-subtle-foreground">{formatMoney(custoDireto)}</span>
          </div>
          <div className="flex items-baseline gap-2.5">
            <span className="text-xs text-muted-foreground">com BDI {orcamentoBdiLabel}</span>
            <span className="font-mono text-[17px] font-extrabold text-success">{formatMoney(comBdi)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const orcamentoBdiLabel = "24,5%";

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-md border border-dashed border-secondary/40 px-3 py-1.25 text-xs font-semibold text-secondary hover:border-secondary hover:bg-secondary/10"
    >
      <Plus className="h-3.25 w-3.25" />
      {label}
    </button>
  );
}
