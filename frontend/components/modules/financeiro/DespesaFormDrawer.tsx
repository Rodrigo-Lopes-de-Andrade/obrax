"use client";

import * as React from "react";
import Decimal from "decimal.js";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { MoneyInput } from "@/components/shared/MoneyInput";
import type { DespesaOut, DespesaUpdate } from "@/lib/api/types";
import { useCategorias } from "@/lib/hooks/use-categorias";
import {
  useCreateDespesa,
  useCreateDespesaParcelada,
  useFasesObra,
  useUpdateDespesa,
} from "@/lib/hooks/use-despesas";
import {
  MAX_PARCELAS,
  MIN_PARCELAS,
  ParcelamentoFields,
  valorMenorQueCentavos,
} from "./ParcelamentoFields";

const schema = z
  .object({
    obra_fase_id: z.string().min(1, "Selecione a fase"),
    categoria_id: z.string().min(1, "Selecione a categoria"),
    fornecedor_nome: z.string().trim().min(1, "Informe o fornecedor").max(200, "Máx. 200 caracteres"),
    descricao: z.string().trim().min(1, "Informe a descrição").max(500, "Máx. 500 caracteres"),
    valor: z.string().min(1, "Informe um valor maior que zero"),
    data_competencia: z.string().min(1, "Informe a data de competência"),
    vencimento: z.string().min(1, "Informe o vencimento"),
    parcelar: z.boolean(),
    numero_parcelas: z.string(),
  })
  .superRefine((v, ctx) => {
    if (!v.parcelar) return;
    const n = Number(v.numero_parcelas);
    if (!Number.isInteger(n) || n < MIN_PARCELAS || n > MAX_PARCELAS) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["numero_parcelas"],
        message: `Informe de ${MIN_PARCELAS} a ${MAX_PARCELAS} parcelas`,
      });
    } else if (v.valor !== "" && valorMenorQueCentavos(v.valor, n)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["valor"],
        message: `O valor deve ser de ao menos ${n} centavos para ${n} parcelas`,
      });
    }
  });

export type DespesaFormValues = z.infer<typeof schema>;

const EMPTY: DespesaFormValues = {
  obra_fase_id: "",
  categoria_id: "",
  fornecedor_nome: "",
  descricao: "",
  valor: "",
  data_competencia: "",
  vencimento: "",
  parcelar: false,
  numero_parcelas: "3",
};

function fromDespesa(d: DespesaOut): DespesaFormValues {
  return {
    obra_fase_id: d.obra_fase_id,
    categoria_id: d.categoria_id,
    fornecedor_nome: d.fornecedor_nome,
    descricao: d.descricao,
    valor: d.valor,
    data_competencia: d.data_competencia,
    vencimento: d.vencimento,
    parcelar: false,
    numero_parcelas: "3",
  };
}

/** PATCH só com o que mudou: o contrato recusa `null` em campo obrigatório. */
function diff(v: DespesaFormValues, d: DespesaOut): DespesaUpdate {
  const out: DespesaUpdate = {};
  if (v.obra_fase_id !== d.obra_fase_id) out.obra_fase_id = v.obra_fase_id;
  if (v.categoria_id !== d.categoria_id) out.categoria_id = v.categoria_id;
  if (v.fornecedor_nome.trim() !== d.fornecedor_nome) out.fornecedor_nome = v.fornecedor_nome.trim();
  if (v.descricao.trim() !== d.descricao) out.descricao = v.descricao.trim();
  if (!new Decimal(v.valor).eq(d.valor)) out.valor = v.valor;
  if (v.data_competencia !== d.data_competencia) out.data_competencia = v.data_competencia;
  if (v.vencimento !== d.vencimento) out.vencimento = v.vencimento;
  return out;
}

interface DespesaFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  obraId: string;
  /** Presente = edição; ausente = lançamento. */
  despesa?: DespesaOut | null;
}

export function DespesaFormDrawer({ open, onOpenChange, obraId, despesa }: DespesaFormDrawerProps) {
  const editing = Boolean(despesa);
  const fasesQ = useFasesObra(obraId);
  const categoriasQ = useCategorias();
  const create = useCreateDespesa(obraId);
  const createParcelada = useCreateDespesaParcelada(obraId);
  const update = useUpdateDespesa(obraId);

  const form = useForm<DespesaFormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (open) form.reset(despesa ? fromDespesa(despesa) : EMPTY);
  }, [open, despesa, form]);

  const fases = React.useMemo(
    () =>
      (fasesQ.data ?? []).filter(
        (f) => f.ativa || f.id === despesa?.obra_fase_id,
      ),
    [fasesQ.data, despesa],
  );
  // Categoria inativa de uma despesa existente continua selecionável na edição.
  const categorias = React.useMemo(() => {
    // CA-F05.4: categoria inativa não é oferecida em despesa nova (defesa além do filtro do servidor).
    const ativas = (categoriasQ.data ?? []).filter((c) => c.ativa);
    if (despesa && !ativas.some((c) => c.id === despesa.categoria_id)) {
      return [
        ...ativas,
        { id: despesa.categoria_id, nome: despesa.categoria_nome, ativa: false, created_at: "" },
      ];
    }
    return ativas;
  }, [categoriasQ.data, despesa]);

  const pending = create.isPending || createParcelada.isPending || update.isPending;
  const parcelar = form.watch("parcelar");
  const semFases = !fasesQ.isLoading && !fasesQ.isError && fases.length === 0;

  function done() {
    onOpenChange(false);
  }

  function onSubmit(v: DespesaFormValues) {
    if (despesa) {
      const data = diff(v, despesa);
      if (Object.keys(data).length === 0) return done();
      return update.mutate({ id: despesa.id, data }, { onSuccess: done });
    }
    const base = {
      obra_fase_id: v.obra_fase_id,
      categoria_id: v.categoria_id,
      fornecedor_nome: v.fornecedor_nome.trim(),
      descricao: v.descricao.trim(),
      valor: v.valor,
      data_competencia: v.data_competencia,
    };
    if (v.parcelar) {
      return createParcelada.mutate(
        { ...base, numero_parcelas: Number(v.numero_parcelas), primeiro_vencimento: v.vencimento },
        { onSuccess: done },
      );
    }
    create.mutate({ ...base, vencimento: v.vencimento }, { onSuccess: done });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{editing ? "Editar despesa" : "Lançar despesa"}</SheetTitle>
          <SheetDescription>
            {editing
              ? "Só os campos alterados são enviados."
              : "Toda despesa é apropriada a uma fase da obra e nasce como prevista."}
          </SheetDescription>
        </SheetHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col" noValidate>
            <div className="flex-1 space-y-4 overflow-y-auto px-4 pb-4">
              {fasesQ.isError ? (
                <p role="alert" className="text-sm text-destructive">
                  Não foi possível carregar as fases da obra.{" "}
                  <button type="button" className="underline" onClick={() => fasesQ.refetch()}>
                    Tentar novamente
                  </button>
                </p>
              ) : semFases ? (
                <p role="alert" className="text-sm text-destructive">
                  Esta obra ainda não tem fases: aprove um orçamento para lançar despesas.
                </p>
              ) : null}

              <FormField
                control={form.control}
                name="obra_fase_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fase</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange} disabled={fasesQ.isLoading}>
                      <FormControl>
                        <SelectTrigger className="w-full" aria-label="Fase">
                          <SelectValue placeholder={fasesQ.isLoading ? "Carregando…" : "Selecione a fase"} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {fases.map((f) => (
                          <SelectItem key={f.id} value={f.id}>
                            {f.codigo} · {f.descricao}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="categoria_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Categoria</FormLabel>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                      disabled={categoriasQ.isLoading}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full" aria-label="Categoria">
                          <SelectValue
                            placeholder={categoriasQ.isLoading ? "Carregando…" : "Selecione a categoria"}
                          />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categorias.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.nome}
                            {c.ativa ? "" : " (inativa)"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="fornecedor_nome"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fornecedor</FormLabel>
                    <FormControl>
                      <Input placeholder="Concreteira Alfa" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="descricao"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição</FormLabel>
                    <FormControl>
                      <Input placeholder="Concreto usinado" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="valor"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{parcelar ? "Valor total" : "Valor"}</FormLabel>
                    <FormControl>
                      <MoneyInput
                        name={field.name}
                        ref={field.ref}
                        onBlur={field.onBlur}
                        value={field.value}
                        onValueChange={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="data_competencia"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Competência</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="vencimento"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{parcelar ? "1º vencimento" : "Vencimento"}</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {editing ? null : <ParcelamentoFields />}
            </div>

            <SheetFooter>
              <Button type="submit" disabled={pending || semFases}>
                {pending ? <Loader2 className="animate-spin" /> : null}
                {editing ? "Salvar alterações" : parcelar ? "Confirmar parcelas" : "Lançar despesa"}
              </Button>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
                Cancelar
              </Button>
            </SheetFooter>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
