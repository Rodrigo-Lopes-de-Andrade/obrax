"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, Camera, ListChecks } from "lucide-react";

import { cn } from "@/lib/utils";

/** Sub-navegação por obra no app de campo (F8): alterna Checklist / Fotos /
 * Ocorrências mantendo a obra atual. Touch targets ≥ 40px. */
export function ObraTabs({ obraId }: { obraId: string }) {
  const pathname = usePathname();
  const tabs = [
    { label: "Checklist", icon: ListChecks, href: `/campo/checklist/${obraId}`, match: "/campo/checklist" },
    { label: "Fotos", icon: Camera, href: `/campo/foto/${obraId}`, match: "/campo/foto" },
    { label: "Ocorrências", icon: AlertTriangle, href: `/campo/ocorrencia/${obraId}`, match: "/campo/ocorrencia" },
  ];

  return (
    <div className="mb-4 grid grid-cols-3 gap-1 rounded-xl bg-muted p-1">
      {tabs.map((t) => {
        const active = pathname.startsWith(t.match);
        return (
          <Link
            key={t.label}
            href={t.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex min-h-[40px] items-center justify-center gap-1.5 rounded-lg px-1.5 text-xs font-semibold transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground active:bg-background/50",
            )}
          >
            <t.icon className="size-4 flex-shrink-0" />
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
