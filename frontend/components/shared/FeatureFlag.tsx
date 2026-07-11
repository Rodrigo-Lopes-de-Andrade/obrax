"use client";

import * as React from "react";

import { useIaEnabled } from "@/lib/hooks/use-ia";

/**
 * Gate de feature flag do Módulo 3 (docs/CLAUDE.md: `ia-module-enabled`,
 * tier Pro/Enterprise). Hoje só existe a flag de IA; o componente encapsula a
 * fonte (mock → PostHog em produção) para os chamadores não dependerem dela.
 *
 * `fallback` é o que aparece quando a flag está desligada (ex.: card de upgrade).
 */
export function FeatureFlag({
  flag,
  children,
  fallback = null,
}: {
  flag: "ia-module-enabled";
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const iaEnabled = useIaEnabled();
  const enabled = flag === "ia-module-enabled" ? iaEnabled : false;
  return <>{enabled ? children : fallback}</>;
}
