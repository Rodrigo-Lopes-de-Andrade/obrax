"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, ListChecks, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import { useFieldStore } from "@/state/field";

/** Navegação inferior do app de campo. Touch targets ≥ 44×44px (critério F7.1),
 * fixa no rodapé com safe-area p/ iOS. */
export function BottomNav() {
  const pathname = usePathname();
  const lastObraId = useFieldStore((s) => s.lastObraId);

  // Evita mismatch de hidratação: o store persistido só é lido após montar.
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  const checklistHref = mounted && lastObraId ? `/campo/checklist/${lastObraId}` : "/campo";

  const items = [
    {
      label: "Obras",
      icon: Building2,
      href: "/campo",
      active: pathname === "/campo",
    },
    {
      label: "Checklist",
      icon: ListChecks,
      href: checklistHref,
      active: pathname.startsWith("/campo/checklist"),
    },
    {
      label: "Sincronizar",
      icon: RefreshCw,
      href: "/campo/offline",
      active: pathname.startsWith("/campo/offline"),
    },
  ];

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur pb-[env(safe-area-inset-bottom)]"
      aria-label="Navegação de campo"
    >
      <div className="mx-auto flex max-w-md items-stretch">
        {items.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            aria-current={item.active ? "page" : undefined}
            className={cn(
              "flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 px-2 py-2 text-[11px] font-medium transition-colors",
              item.active ? "text-primary" : "text-muted-foreground active:bg-muted",
            )}
          >
            <item.icon className="size-5.5" />
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
