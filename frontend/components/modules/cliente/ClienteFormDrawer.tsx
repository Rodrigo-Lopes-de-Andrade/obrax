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
import type { Cliente } from "@/lib/api/types";
import { useCreateCliente } from "@/lib/hooks/use-clientes";

const schema = z.object({
  tipo_pessoa: z.enum(["PF", "PJ"]),
  documento: z.string().trim().min(1, "Informe o CPF/CNPJ"),
  nome: z.string().trim().min(1, "Informe o nome"),
  telefone: z.string(),
  email: z.union([z.literal(""), z.string().email("E-mail inválido")]),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = {
  tipo_pessoa: "PJ",
  documento: "",
  nome: "",
  telefone: "",
  email: "",
};

interface ClienteFormDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Chamado com o cliente recém-criado (ex.: para auto-selecionar no form de obra). */
  onCreated?: (cliente: Cliente) => void;
}

export function ClienteFormDrawer({ open, onOpenChange, onCreated }: ClienteFormDrawerProps) {
  const createCliente = useCreateCliente();
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: EMPTY });

  React.useEffect(() => {
    if (open) form.reset(EMPTY);
  }, [open, form]);

  async function onSubmit(values: FormValues) {
    const orNull = (s: string) => (s.trim() === "" ? null : s.trim());
    const cliente = await createCliente.mutateAsync({
      tipo_pessoa: values.tipo_pessoa,
      documento: values.documento.replace(/\D/g, ""),
      nome: values.nome.trim(),
      telefone: orNull(values.telefone),
      email: orNull(values.email),
    });
    onCreated?.(cliente);
    onOpenChange(false);
  }

  const tipo = form.watch("tipo_pessoa");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Novo cliente</SheetTitle>
          <SheetDescription>Cadastre um cliente para vincular às obras.</SheetDescription>
        </SheetHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto px-4 pb-4">
              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="tipo_pessoa"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-full" aria-label="Tipo de pessoa">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="PJ">Pessoa Jurídica</SelectItem>
                          <SelectItem value="PF">Pessoa Física</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
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
                    <FormLabel>Nome / Razão social</FormLabel>
                    <FormControl>
                      <Input placeholder="Eficienge Construções Ltda" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="telefone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Telefone</FormLabel>
                      <FormControl>
                        <Input placeholder="(11) 90000-0000" {...field} />
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
                      <FormLabel>E-mail</FormLabel>
                      <FormControl>
                        <Input type="email" placeholder="contato@empresa.com" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <SheetFooter>
              <Button type="submit" disabled={createCliente.isPending}>
                {createCliente.isPending ? <Loader2 className="animate-spin" /> : null}
                Criar cliente
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={createCliente.isPending}
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
