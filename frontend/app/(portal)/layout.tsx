import type { Metadata } from "next";

import { HardHat } from "lucide-react";

export const metadata: Metadata = {
  title: "Portal do Cliente — Obrax",
  description: "Acompanhe sua obra: andamento, documentos, fotos e orçamento",
};

/**
 * Layout do portal do cliente (F9.1). Template separado do admin: sem sidebar,
 * sem chrome interno — uma coluna central, limpa, com a marca no topo. É o único
 * ambiente sem autenticação por sessão (o acesso é o token na URL).
 */
export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/20 text-foreground">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-2.5 px-4 py-3.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <HardHat className="size-4.5" />
          </div>
          <span className="text-lg font-extrabold tracking-tight">Obrax</span>
          <span className="text-sm text-muted-foreground">· Portal do Cliente</span>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 py-6">{children}</main>
      <footer className="mx-auto w-full max-w-3xl px-4 pb-8 pt-4 text-center text-xs text-muted-foreground">
        Acesso exclusivo ao cliente · dados protegidos conforme a LGPD
      </footer>
    </div>
  );
}
