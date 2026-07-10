"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Images, MessagesSquare } from "lucide-react";

import { cn } from "@/lib/utils";

/** Sub-navegação do portal (F9.1): Obra · Orçamento · Chamados. */
export function PortalNav({ token }: { token: string }) {
  const pathname = usePathname();
  const base = `/obra/${token}`;
  const tabs = [
    { href: base, label: "Obra", icon: Images, exact: true },
    { href: `${base}/orcamento`, label: "Orçamento", icon: FileText, exact: false },
    { href: `${base}/tickets`, label: "Chamados", icon: MessagesSquare, exact: false },
  ];

  return (
    <nav className="mb-5 flex gap-1 rounded-xl border border-border bg-card p-1">
      {tabs.map((t) => {
        const active = t.exact ? pathname === t.href : pathname.startsWith(t.href);
        const Icon = t.icon;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted",
            )}
          >
            <Icon className="size-4" />
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
