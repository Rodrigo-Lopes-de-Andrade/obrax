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
import { createOrcamento } from "@/lib/api/orcamentos";
import { useObras } from "@/lib/hooks/use-obras";

const schema = z.object({
  obra_id: z.string().min(1, "Selecione uma obra"),
  titulo: z.string().trim().min(1, "Informe o título").max(200, "Máx. 200 caracteres"),
});

type FormValues = z.infer<typeof schema>;

const EMPTY: FormValues = { obra_id: "", titulo: "" };

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  obraId?: string;
}

export function CreateOrcamentoDrawer({ open, onOpenChange, obraId }: Props) {
  const router = useRouter();
  const { data: obrasPage, isLoading: obrasLoading } = useObras({ limit: 100 });
  const [pending, setPending] = React.useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (open) form.reset({ ...EMPTY, obra_id: obraId ?? "" });
  }, [open, obraId, form]);

  async function onSubmit(values: FormValues) {
    setPending(true);
    try {
      const detail = await createOrcamento(values.obra_id, {
        titulo: values.titulo.trim(),
      });
      onOpenChange(false);
      // Vai direto pro builder da versão recém-criada.
      router.push(`/orcamentos/${detail.id}/edit`);
    } finally {
      setPending(false);
    }
  }

  const obras = obrasPage?.items ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Novo orçamento</SheetTitle>
          <SheetDescription>
            Cria a revisão 1 (vazia). Monte a EAP no builder logo em seguida.
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
                      <Input placeholder="Orçamento Executivo — Rev. 1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <SheetFooter>
              <Button type="submit" disabled={pending}>
                {pending ? <Loader2 className="animate-spin" /> : null}
                Criar e abrir builder
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
