"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
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
import { Textarea } from "@/components/ui/textarea";
import { useObras } from "@/lib/hooks/use-obras";
import { useCreateTicket } from "@/lib/hooks/use-tickets";

const schema = z.object({
  obra_id: z.string().min(1, "Selecione uma obra"),
  titulo: z.string().trim().min(1, "Informe o título").max(200, "Máx. 200 caracteres"),
  descricao: z.string().max(5000, "Máx. 5000 caracteres"),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = { obra_id: "", titulo: "", descricao: "" };

interface CreateTicketDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pré-seleciona a obra (ex.: abrir chamado a partir da tela da obra). */
  obraId?: string;
}

export function CreateTicketDrawer({
  open,
  onOpenChange,
  obraId,
}: CreateTicketDrawerProps) {
  const router = useRouter();
  const { data: obrasPage, isLoading: obrasLoading } = useObras({ limit: 100 });
  const createTicket = useCreateTicket();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (open) form.reset({ ...EMPTY, obra_id: obraId ?? "" });
  }, [open, obraId, form]);

  function onSubmit(values: FormValues) {
    createTicket.mutate(
      {
        obraId: values.obra_id,
        data: {
          titulo: values.titulo.trim(),
          descricao: values.descricao.trim() || null,
        },
      },
      {
        onSuccess: (ticket) => {
          onOpenChange(false);
          router.push(`/tickets/${ticket.id}`);
        },
      },
    );
  }

  const obras = obrasPage?.items ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Novo chamado</SheetTitle>
          <SheetDescription>
            Abra um chamado vinculado a uma obra. A equipe é notificada por e-mail.
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
                name="obra_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Obra</FormLabel>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                      disabled={Boolean(obraId) || obrasLoading}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue
                            placeholder={obrasLoading ? "Carregando…" : "Selecione uma obra"}
                          />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {obras.map((o) => (
                          <SelectItem key={o.id} value={o.id}>
                            {o.codigo} · {o.nome}
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
                name="titulo"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Título</FormLabel>
                    <FormControl>
                      <Input placeholder="Vazamento na laje do 3º pavimento" {...field} />
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
                    <FormLabel>Descrição (opcional)</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={5}
                        placeholder="Descreva o problema, quando começou e o impacto na obra…"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <SheetFooter>
              <Button type="submit" disabled={createTicket.isPending}>
                {createTicket.isPending ? <Loader2 className="animate-spin" /> : null}
                Abrir chamado
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={createTicket.isPending}
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
