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
import type { Cliente, ClienteCreateInput } from "@/lib/api/types";
import { useCreateCliente, useUpdateCliente } from "@/lib/hooks/use-clientes";
import { formatDocumento, isValidDocumento, onlyDigits } from "./documento";

const schema = z
  .object({
    tipo_pessoa: z.enum(["PF", "PJ"]),
    documento: z.string().trim().min(1, "Informe o documento"),
    nome: z.string().trim().min(1, "Informe o nome"),
    telefone: z.string(),
    email: z.union([z.literal(""), z.string().trim().email("E-mail inválido")]),
  })
  .refine((v) => isValidDocumento(v.tipo_pessoa, v.documento), {
    path: ["documento"],
    message: "Documento inválido — confira os dígitos",
  });

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = { tipo_pessoa: "PJ", documento: "", nome: "", telefone: "", email: "" };

function toFormValues(c: Cliente): FormValues {
  return {
    tipo_pessoa: c.tipo_pessoa,
    documento: formatDocumento(c.documento),
    nome: c.nome,
    telefone: c.telefone ?? "",
    email: c.email ?? "",
  };
}

interface ClienteFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Presente = modo edição; ausente = criação. */
  cliente?: Cliente;
  /** Chamado com o cliente salvo — a "Nova obra" usa para já selecioná-lo. */
  onSaved?: (cliente: Cliente) => void;
}

export function ClienteFormDrawer({ open, onOpenChange, cliente, onSaved }: ClienteFormDrawerProps) {
  const isEdit = Boolean(cliente);
  const createCliente = useCreateCliente();
  const updateCliente = useUpdateCliente();
  const pending = createCliente.isPending || updateCliente.isPending;

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: EMPTY });
  const tipo = form.watch("tipo_pessoa");

  React.useEffect(() => {
    if (open) form.reset(cliente ? toFormValues(cliente) : EMPTY);
  }, [open, cliente, form]);

  function onSubmit(values: FormValues) {
    const orNull = (s: string) => (s.trim() === "" ? null : s.trim());
    const data: ClienteCreateInput = {
      tipo_pessoa: values.tipo_pessoa,
      documento: onlyDigits(values.documento),
      nome: values.nome.trim(),
      telefone: orNull(values.telefone),
      email: orNull(values.email),
    };
    const done = (saved: Cliente) => {
      onSaved?.(saved);
      onOpenChange(false);
    };
    if (isEdit && cliente) {
      updateCliente.mutate({ id: cliente.id, data }, { onSuccess: done });
    } else {
      createCliente.mutate(data, { onSuccess: done });
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{isEdit ? "Editar cliente" : "Novo cliente"}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? "Atualize os dados do cliente."
              : "Cadastre o cliente (pessoa física ou empresa) dono da obra."}
          </SheetDescription>
        </SheetHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto px-4 pb-4">
              <div className="grid grid-cols-[130px_1fr] gap-3">
                <FormField
                  control={form.control}
                  name="tipo_pessoa"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={(v) => {
                          field.onChange(v);
                          form.clearErrors("documento");
                        }}
                      >
                        <FormControl>
                          <SelectTrigger className="w-full" aria-label="Tipo de pessoa">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="PJ">Empresa</SelectItem>
                          <SelectItem value="PF">Pessoa física</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="documento"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{tipo === "PF" ? "CPF" : "CNPJ"}</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="numeric"
                          placeholder={tipo === "PF" ? "000.000.000-00" : "00.000.000/0000-00"}
                          {...field}
                          onBlur={(e) => {
                            field.onChange(formatDocumento(e.target.value));
                            field.onBlur();
                          }}
                        />
                      </FormControl>
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
                    <FormLabel>{tipo === "PF" ? "Nome" : "Razão social / nome"}</FormLabel>
                    <FormControl>
                      <Input placeholder={tipo === "PF" ? "Maria Souza" : "Construtora Exemplo Ltda"} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="telefone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Telefone (opcional)</FormLabel>
                    <FormControl>
                      <Input type="tel" placeholder="(11) 99999-0000" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>E-mail (opcional)</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="contato@cliente.com.br" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <SheetFooter>
              <Button type="submit" disabled={pending}>
                {pending ? <Loader2 className="animate-spin" /> : null}
                {isEdit ? "Salvar alterações" : "Cadastrar cliente"}
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
