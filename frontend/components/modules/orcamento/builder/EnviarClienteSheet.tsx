"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Copy, Loader2, Mail, MessageCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { gerarPortalLink } from "@/lib/api/portal";
import { formatDate, formatMoney } from "@/lib/format";
import { useClientes } from "@/lib/hooks/use-clientes";
import { useObra } from "@/lib/hooks/use-obras";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  obraId: string;
  titulo: string;
  precoVenda: string | null | undefined;
}

/** Envio do orçamento ao cliente (US-17). O backend ainda não envia e-mail nem
 * WhatsApp (notifier no-op), então o envio sai pelos apps do próprio usuário:
 * gera o link do portal (POST /obras/{id}/portal-link) e abre wa.me / mailto já
 * com destinatário e mensagem. */
export function EnviarClienteSheet({ open, onOpenChange, obraId, titulo, precoVenda }: Props) {
  const { data: obra } = useObra(obraId);
  const { data: clientesPage } = useClientes();
  const cliente = clientesPage?.items.find((c) => c.id === obra?.cliente_id);

  const link = useMutation({ mutationFn: () => gerarPortalLink(obraId) });
  const [copiado, setCopiado] = React.useState(false);

  // Gera um link novo a cada abertura (o token expira; o anterior segue válido).
  const { mutate, reset } = link;
  React.useEffect(() => {
    if (open && obraId) mutate();
    if (!open) {
      reset();
      setCopiado(false);
    }
  }, [open, obraId, mutate, reset]);

  const url = link.data ? `${window.location.origin}${link.data.url}` : null;
  const saudacao = cliente ? `Olá, ${cliente.nome.split(" ")[0]}!` : "Olá!";
  const mensagem = url
    ? `${saudacao} Segue o orçamento "${titulo}"${obra ? ` da obra ${obra.nome}` : ""}` +
      `${precoVenda ? `, no valor de ${formatMoney(precoVenda)}` : ""}.\n\n` +
      `Para ver os detalhes e aprovar, acesse:\n${url}`
    : "";

  const telefone = cliente?.telefone?.replace(/\D/g, "") ?? "";
  // wa.me exige DDI: número brasileiro sem 55 (10–11 dígitos) ganha o prefixo.
  const whatsNumero = telefone.length === 10 || telefone.length === 11 ? `55${telefone}` : telefone;
  const whatsHref = `https://wa.me/${whatsNumero}?text=${encodeURIComponent(mensagem)}`;
  const mailHref =
    `mailto:${cliente?.email ?? ""}?subject=${encodeURIComponent(`Orçamento: ${titulo}`)}` +
    `&body=${encodeURIComponent(mensagem)}`;

  async function copiar() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopiado(true);
      toast.success("Link copiado");
    } catch {
      toast.error("Não foi possível copiar — selecione o link e copie manualmente.");
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Enviar ao cliente</SheetTitle>
          <SheetDescription>
            {cliente
              ? `O cliente ${cliente.nome} recebe um link para ver e aprovar o orçamento.`
              : "O cliente recebe um link para ver e aprovar o orçamento."}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 px-4 pb-6">
          {link.isError ? (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
              Não foi possível gerar o link.{" "}
              <button type="button" className="underline" onClick={() => mutate()}>
                Tentar de novo
              </button>
            </div>
          ) : !url ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Gerando link do portal…
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <label htmlFor="portal-link" className="text-sm font-medium">
                  Link do portal
                </label>
                <div className="flex gap-2">
                  <input
                    id="portal-link"
                    readOnly
                    value={url}
                    onFocus={(e) => e.currentTarget.select()}
                    className="min-w-0 flex-1 rounded-md border border-border bg-muted px-2.5 py-1.5 text-xs text-muted-foreground"
                  />
                  <Button type="button" variant="outline" size="sm" onClick={copiar}>
                    {copiado ? <Check /> : <Copy />}
                    {copiado ? "Copiado" : "Copiar"}
                  </Button>
                </div>
                {link.data && (
                  <p className="text-xs text-muted-foreground">
                    Válido até {formatDate(link.data.expires_at)}.
                  </p>
                )}
              </div>

              <div className="grid gap-2">
                <Button asChild>
                  <a href={whatsHref} target="_blank" rel="noopener noreferrer">
                    <MessageCircle />
                    Enviar pelo WhatsApp
                  </a>
                </Button>
                <Button asChild variant="outline">
                  <a href={mailHref}>
                    <Mail />
                    Enviar por e-mail
                  </a>
                </Button>
              </div>

              {cliente && (!cliente.telefone || !cliente.email) && (
                <p className="text-xs text-muted-foreground">
                  {!cliente.telefone && !cliente.email
                    ? "O cliente não tem telefone nem e-mail cadastrados"
                    : !cliente.telefone
                      ? "O cliente não tem telefone cadastrado"
                      : "O cliente não tem e-mail cadastrado"}{" "}
                  — você escolhe o contato no WhatsApp/e-mail, ou completa o cadastro em Clientes.
                </p>
              )}

              <div className="space-y-1.5">
                <p className="text-sm font-medium">Mensagem</p>
                <p className="rounded-md border border-border bg-muted/50 px-3 py-2 text-xs whitespace-pre-line text-muted-foreground">
                  {mensagem}
                </p>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
