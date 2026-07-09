"use client";

import { useQuery } from "@tanstack/react-query";

import { getDashboardSummary } from "@/lib/api/dashboard";

export const dashboardKeys = {
  summary: ["dashboard", "summary"] as const,
};

/** KPIs do dashboard admin (B4.4). `staleTime` espelha o cache de 60s do backend. */
export function useDashboardSummary() {
  return useQuery({
    queryKey: dashboardKeys.summary,
    queryFn: getDashboardSummary,
    staleTime: 60_000,
  });
}
