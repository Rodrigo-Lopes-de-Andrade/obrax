"use client";

import * as React from "react";
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
import type { Obra, ObraCreateInput, ObraUpdateInput } from "@/lib/api/types";
import { useClientes } from "@/lib/hooks/use-clientes";
import { useCreateObra, useUpdateObra } from "@/lib/hooks/use-obras";
import { OBRA_STATUS_OPTIONS } from "./status";

const schema = z
  .object({
    cliente_id: z.string().min(1, "Selecione um cliente"),
    codigo: z.string().trim().min(1, "Informe o código"),
    nome: z.string().trim().min(1, "Informe o nome"),
    status: z.enum([
      "planejamento",
      "execucao",
      "pausada",
      "concluida",
      "cancelada",
    ]),
    data_inicio: z.string(),
    data_prevista_fim: z.string(),
    valor_contrato: z.string(),
  })
  .refine(
    (v) =>
      !v.data_inicio ||
      !v.data_prevista_fim ||
      v.data_prevista_fim >= v.data_inicio,
    { path: ["data_prevista_fim"], message: "Fim não pode ser antes do início" },
  )
  .refine(
    (v) => {
      if (!v.valor_contrato.trim()) return true;
      const n = Number(v.valor_contrato.replace(",", "."));
      return !Number.isNaN(n) && n >= 0;
    },
    { path: ["valor_contrato"], message: "Valor inválido" },
  );

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = {
  cliente_id: "",
  codigo: "",
  nome: "",
  status: "planejamento",
  data_inicio: "",
  data_prevista_fim: "",
  valor_contrato: "",
};

function toFormValues(obra: Obra): FormValues {
  return {
    cliente_id: obra.cliente_id,
    codigo: obra.codigo,
    nome: obra.nome,
    status: obra.status,
    data_inicio: obra.data_inicio ?? "",
    data_prevista_fim: obra.data_prevista_fim ?? "",
    valor_contrato: obra.valor_contrato ?? "",
  };
}

interface ObraFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Presente = modo edição; ausente = criação. */
  obra?: Obra;
}

export function ObraFormDrawer({ open, onOpenChange, obra }: ObraFormDrawerProps) {
  const isEdit = Boolean(obra);
  const { data: clientesPage, isLoading: clientesLoading } = useClientes();
  const createObra = useCreateObra();
  const updateObra = useUpdateObra();
  const pending = createObra.isPending || updateObra.isPending;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (open) form.reset(obra ? toFormValues(obra) : EMPTY);
  }, [open, obra, form]);

  function onSubmit(values: FormValues) {
    const orNull = (s: string) => (s.trim() === "" ? null : s.trim());
    const valor = values.valor_contrato.trim()
      ? values.valor_contrato.replace(",", ".").trim()
      : null;

    if (isEdit && obra) {
      const data: ObraUpdateInput = {
        codigo: values.codigo.trim(),
        nome: values.nome.trim(),
        status: values.status,
        data_inicio: orNull(values.data_inicio),
        data_prevista_fim: orNull(values.data_prevista_fim),
        valor_contrato: valor,
      };
      updateObra.mutate(
        { id: obra.id, data },
        { onSuccess: () => onOpenChange(false) },
      );
    } else {
      const data: ObraCreateInput = {
        cliente_id: values.cliente_id,
        codigo: values.codigo.trim(),
        nome: values.nome.trim(),
        status: values.status,
        data_inicio: orNull(values.data_inicio),
        data_prevista_fim: orNull(values.data_prevista_fim),
        valor_contrato: valor,
      };
      createObra.mutate(data, { onSuccess: () => onOpenChange(false) });
    }
  }

  const clientes = clientesPage?.items ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{isEdit ? "Editar obra" : "Nova obra"}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? "Atualize os dados da obra. O cliente não pode ser alterado."
              : "Cadastre uma nova obra vinculada a um cliente."}
          </SheetDescription>
        </SheetHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="flex-1 space-y-4 overflow-y-auto px-4 pb-4">
              <FormField
                control={form.control}
                name="cliente_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cliente</FormLabel>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                      disabled={isEdit || clientesLoading}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue
                            placeholder={
                              clientesLoading ? "Carregando…" : "Selecione um cliente"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {clientes.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="codigo"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Código</FormLabel>
                      <FormControl>
                        <Input placeholder="OBR-1042" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {OBRA_STATUS_OPTIONS.map((o) => (
                            <SelectItem key={o.value} value={o.value}>
                              {o.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="nome"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome</FormLabel>
                    <FormControl>
                      <Input placeholder="Residencial Jardim das Acácias" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="data_inicio"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Início</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="data_prevista_fim"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Previsão de fim</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="valor_contrato"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Valor do contrato (R$)</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" placeholder="480000.00" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <SheetFooter>
              <Button type="submit" disabled={pending}>
                {pending ? <Loader2 className="animate-spin" /> : null}
                {isEdit ? "Salvar alterações" : "Criar obra"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={pending}
              >
                Cancelar
              </Button>
            </SheetFooter>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
