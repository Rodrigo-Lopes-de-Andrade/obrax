"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { useObra } from "@/lib/hooks/use-obras";
import { cn } from "@/lib/utils";

const TABS = [
  { label: "Documentos", seg: "documentos" },
  { label: "Equipe", seg: "equipes" },
];

export function ObraDetailHeader({ obraId }: { obraId: string }) {
  const pathname = usePathname();
  const { data: obra } = useObra(obraId);

  return (
    <div className="space-y-4 border-b border-border">
      <div>
        <Link
          href="/obras"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Obras
        </Link>
        {obra ? (
          <>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">
              {obra.nome}
            </h1>
            <p className="font-mono text-xs text-muted-foreground">
              {obra.codigo}
            </p>
          </>
        ) : (
          <div className="mt-2 h-5 w-48 animate-pulse rounded bg-muted" />
        )}
      </div>

      <nav className="flex gap-1">
        {TABS.map((t) => {
          const href = `/obras/${obraId}/${t.seg}`;
          const active = pathname === href;
          return (
            <Link
              key={t.seg}
              href={href}
              className={cn(
                "border-b-2 px-3 pb-2.5 text-sm font-medium transition-colors",
                active
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
