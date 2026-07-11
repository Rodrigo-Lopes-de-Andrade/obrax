"use client";

import Link from "next/link";
import { Lock } from "lucide-react";

import { FeatureFlag } from "@/components/shared/FeatureFlag";
import { Button } from "@/components/ui/button";

/** Gate do Módulo 3 (docs/CLAUDE.md): tier Basic vê o bloqueio + upgrade; a API
 * retornaria 403 com upgrade_url. No mock a flag vem ligada. */
export default function IaLayout({ children }: { children: React.ReactNode }) {
  return (
    <FeatureFlag
      flag="ia-module-enabled"
      fallback={
        <div className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-xl border border-border bg-card px-6 py-14 text-center">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
            <Lock className="size-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold">Recurso do plano Pro</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Os Agentes IA estão disponíveis nos planos Pro e Enterprise. Faça upgrade para
              consultar obras e registrar compras pelo WhatsApp.
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard">Ver planos</Link>
          </Button>
        </div>
      }
    >
      {children}
    </FeatureFlag>
  );
}
